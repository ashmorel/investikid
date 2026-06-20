import json
import logging

from app.services.llm_client import get_llm_client
from app.services.llm_json import extract_json_list
from app.services.market_curriculum.backbone import BACKBONE
from app.services.market_curriculum.types import CurriculumProposal, ValidationReport
from app.services.market_curriculum.validator import validate

logger = logging.getLogger(__name__)


class CurriculumDesignError(Exception):
    """The model failed to return a usable curriculum after a retry."""


def _system_prompt(market_code: str, brief_json: dict, gap_note: str = "") -> str:
    backbone = "; ".join(f"{c['key']} ({c['title']}: {c['description']})" for c in BACKBONE)
    return (
        f"You are designing a complete, original financial-education curriculum for the "
        f"market '{market_code}', for children roughly aged 8-16. Ground every module and "
        f"example ONLY in these verified local facts (products, regulators, currency, "
        f"culture): {json.dumps(brief_json, ensure_ascii=False)}. This is NOT a UK curriculum "
        f"— never use UK-specific products, regulators (e.g. FCA), accounts (e.g. ISA) or the "
        f"pound unless the facts say so.\n\n"
        f"COVER every one of these core concepts in at least one level, but design your own "
        f"modules, titles, ordering, depth and local topics around them: {backbone}.\n\n"
        f"SPIRAL: assign every level a complexity_tier of 1 (foundational), 2 (developing) or "
        f"3 (advanced). The curriculum must span all three tiers, earlier levels shallower and "
        f"later levels deeper; when a concept recurs it must get DEEPER, never shallower.\n\n"
        f"{gap_note}"
        f"Respond with ONLY a JSON object: {{\"modules\": [{{\"topic\": str (<=30 chars), "
        f"\"title\": str, \"icon\": one emoji, \"min_age\": int, \"max_age\": int, "
        f"\"order_index\": int, \"levels\": [{{\"title\": str, \"order_index\": int, "
        f"\"complexity_tier\": 1|2|3, \"learning_objective\": str, \"concepts\": [str, ...], "
        f"\"backbone_keys\": [key, ...]}}]}}]}}."
    )


def _parse(raw: str, market_code: str) -> CurriculumProposal | None:
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    modules = parsed.get("modules") if isinstance(parsed, dict) else None
    if modules is None:
        modules = extract_json_list(parsed)  # tolerate a wrapped/top-level list
    if not modules:  # if modules is empty after extraction, treat as unparseable
        return None
    try:
        return CurriculumProposal(market_code=market_code, modules=modules)
    except (ValueError, TypeError):
        return None


async def design_curriculum(
    market_code: str, brief_json: dict
) -> tuple[CurriculumProposal, ValidationReport]:
    client = get_llm_client("premium")
    gap_note = ""
    proposal: CurriculumProposal | None = None
    report: ValidationReport | None = None

    for attempt in range(2):
        raw = await client.complete(
            system_prompt=_system_prompt(market_code, brief_json, gap_note),
            messages=[{"role": "user",
                       "content": f"Design the curriculum for market {market_code}."}],
            temperature=0.5, max_tokens=4000, response_format="json",
        )
        parsed = _parse(raw, market_code)
        if parsed is None:
            continue
        proposal = parsed
        report = validate(proposal)
        if report.ok:
            return proposal, report
        gap_note = (
            f"Your previous attempt had problems: missing concepts "
            f"{report.missing_backbone}; tier regressions {report.regressions}; "
            f"spans all tiers={report.spans_all_tiers}. Fix them.\n\n"
        )

    if proposal is None or report is None:
        raise CurriculumDesignError(f"No usable curriculum for {market_code}")
    return proposal, report  # residual gaps surfaced to the operator
