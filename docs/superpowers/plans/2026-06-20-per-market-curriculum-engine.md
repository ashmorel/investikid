# Per-Market Curriculum Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each market its own independent, market-native curriculum (designer → operator review → materialise → native generation → inline draft review/publish), retiring the from-GB currency-swap path.

**Architecture:** A premium-LLM *curriculum designer* proposes a full module/level/concept tree for a market, grounded only in its verified `MarketBrief` and a fixed must-cover concept backbone, with a per-level complexity tier (spiral). The proposal persists in a new `market_curriculum_proposal` table for operator review (coverage chips); on accept it materialises `Module`/`Level` rows (`has_content` stays false at market level), then a native-generation batch fills each level from the proposal's concepts+tier. Drafts are reviewed and published inline in the Market Content tab.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres (backend); React 18 + Vite + TanStack Query + Tailwind v4 + i18next (frontend); pytest + vitest/vitest-axe.

## Global Constraints

- Repo root `/Users/leeashmore/investikid`; backend cmds from `backend/`, frontend from `frontend/`. venv at `/Users/leeashmore/Local Repo/.venv`.
- Backend test: `/Users/leeashmore/Local\ Repo/.venv/bin/pytest`; lint: `/Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`.
- Async tests use `pytestmark = pytest.mark.asyncio(loop_scope="session")` + `client`/`admin_client`/`db_session` fixtures — never a raw `AsyncClient`.
- DB change = hand-written, chained Alembic migration; run `alembic heads` from `backend/` first and chain off the single head. **Ask the user before any production migration whether to snapshot first.**
- LLM premium client: `get_llm_client("premium").complete(system_prompt=..., messages=[{"role":"user","content":...}], temperature=..., max_tokens=..., response_format="json")`. `response_format="json"` forces an OBJECT wrapper — any top-level array must go through `extract_json_list` (`app/services/llm_json.py`). LLM output that reaches a child must be moderated (native generation already calls `moderate_output`).
- Premium-LLM admin endpoints are rate-limited `@limiter.limit("5/minute")` and call `require_verified_brief(session, market_code)` (`app/services/market_brief_service.py`) — 409 if the brief is not verified.
- Frontend: branch new work in feature commits on `testing`; new UI needs `npx tsc -b`, `npm run lint`, `npm run test`, `npm run build`, and `vitest-axe` on new components. Keep WCAG 2.2 AA.
- Commit messages end with `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- New backend code lives under `backend/app/services/market_curriculum/`.

---

### Task 1: Concept backbone (static data)

**Files:**
- Create: `backend/app/services/market_curriculum/__init__.py` (empty)
- Create: `backend/app/services/market_curriculum/backbone.py`
- Test: `backend/tests/test_curriculum_backbone.py`

**Interfaces:**
- Produces: `BACKBONE: list[ConceptDef]` where `ConceptDef = TypedDict('ConceptDef', {'key': str, 'title': str, 'description': str})`; `backbone_keys() -> set[str]`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_backbone.py
from app.services.market_curriculum.backbone import BACKBONE, backbone_keys

def test_backbone_has_nine_unique_concepts():
    keys = [c["key"] for c in BACKBONE]
    assert len(keys) == 9
    assert len(set(keys)) == 9
    assert backbone_keys() == set(keys)

def test_tax_and_giving_is_required():
    assert "tax_giving" in backbone_keys()

def test_every_concept_has_title_and_description():
    for c in BACKBONE:
        assert c["title"] and c["description"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_backbone.py -q`
Expected: FAIL (ModuleNotFoundError).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/market_curriculum/backbone.py
"""The must-cover concept backbone every market curriculum must satisfy.

Each market is free to add more topics, order them, choose depth, and write all
examples itself — but every key below must be covered by at least one level.
"""
from typing import TypedDict


class ConceptDef(TypedDict):
    key: str
    title: str
    description: str


BACKBONE: list[ConceptDef] = [
    {"key": "earning_income", "title": "Earning & income",
     "description": "Where money comes from and the value of work."},
    {"key": "spending_budgeting", "title": "Spending & budgeting",
     "description": "Needs vs wants and making a plan for money."},
    {"key": "saving_goals", "title": "Saving & goals",
     "description": "Setting money aside for short- and long-term goals."},
    {"key": "banking_accounts", "title": "Banking & accounts",
     "description": "Keeping money safe and how accounts work."},
    {"key": "borrowing_debt", "title": "Borrowing & debt",
     "description": "Credit, the interest you pay, and borrowing wisely."},
    {"key": "growing_compound", "title": "Growing money & compound interest",
     "description": "Investing basics and how money grows over time."},
    {"key": "risk_diversification", "title": "Risk & diversification",
     "description": "Why values change and not putting all eggs in one basket."},
    {"key": "safety_scams", "title": "Financial safety & scams",
     "description": "Protecting money and spotting fraud."},
    {"key": "tax_giving", "title": "Tax & giving",
     "description": "How tax works locally and the role of charitable giving."},
]


def backbone_keys() -> set[str]:
    return {c["key"] for c in BACKBONE}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_backbone.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_curriculum/__init__.py backend/app/services/market_curriculum/backbone.py backend/tests/test_curriculum_backbone.py
git commit -m "feat(curriculum): must-cover concept backbone (9 incl. tax & giving)"
```

---

### Task 2: Coverage + progression validator

**Files:**
- Create: `backend/app/services/market_curriculum/types.py`
- Create: `backend/app/services/market_curriculum/validator.py`
- Test: `backend/tests/test_curriculum_validator.py`

**Interfaces:**
- Consumes: `backbone_keys()` from Task 1.
- Produces:
  - `types.py`: Pydantic models `LevelNode(title:str, order_index:int, complexity_tier:int, learning_objective:str, concepts:list[str], backbone_keys:list[str], level_id:str|None=None)`; `ModuleNode(topic:str, title:str, icon:str, min_age:int, max_age:int, order_index:int, levels:list[LevelNode])`; `CurriculumProposal(market_code:str, modules:list[ModuleNode])`; `ValidationReport(ok:bool, missing_backbone:list[str], tiers_present:list[int], spans_all_tiers:bool, regressions:list[str])`.
  - `validator.py`: `validate(proposal: CurriculumProposal) -> ValidationReport`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_validator.py
from app.services.market_curriculum.types import CurriculumProposal, ModuleNode, LevelNode
from app.services.market_curriculum.validator import validate

def _mod(order, *levels):
    return ModuleNode(topic="t", title="M", icon="💵", min_age=10, max_age=14,
                      order_index=order, levels=list(levels))

def _lvl(order, tier, *keys):
    return LevelNode(title="L", order_index=order, complexity_tier=tier,
                     learning_objective="o", concepts=["c"], backbone_keys=list(keys))

ALL = ["earning_income","spending_budgeting","saving_goals","banking_accounts",
       "borrowing_debt","growing_compound","risk_diversification","safety_scams","tax_giving"]

def _full_proposal():
    # one level per backbone key, tiers spread 1→3, non-decreasing per key
    levels = [_lvl(i, 1 + i // 3, k) for i, k in enumerate(ALL)]
    return CurriculumProposal(market_code="US", modules=[_mod(0, *levels)])

def test_well_formed_proposal_passes():
    rep = validate(_full_proposal())
    assert rep.ok and rep.missing_backbone == [] and rep.spans_all_tiers

def test_missing_backbone_key_flagged():
    p = _full_proposal()
    p.modules[0].levels = p.modules[0].levels[:-1]  # drop tax_giving
    rep = validate(p)
    assert not rep.ok and "tax_giving" in rep.missing_backbone

def test_all_foundational_does_not_span_tiers():
    levels = [_lvl(i, 1, k) for i, k in enumerate(ALL)]
    rep = validate(CurriculumProposal(market_code="US", modules=[_mod(0, *levels)]))
    assert not rep.spans_all_tiers and not rep.ok

def test_tier_regression_flagged():
    # saving_goals appears at tier 3 then again later at tier 2 → regression
    levels = [_lvl(i, 1 + i // 3, k) for i, k in enumerate(ALL)]
    levels.append(_lvl(99, 2, "saving_goals"))
    levels[2] = _lvl(2, 3, "saving_goals")
    rep = validate(CurriculumProposal(market_code="US", modules=[_mod(0, *levels)]))
    assert not rep.ok and any("saving_goals" in r for r in rep.regressions)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_validator.py -q`
Expected: FAIL (import error).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/services/market_curriculum/types.py
from pydantic import BaseModel, Field


class LevelNode(BaseModel):
    title: str
    order_index: int
    complexity_tier: int = Field(ge=1, le=3)
    learning_objective: str
    concepts: list[str]
    backbone_keys: list[str] = []
    level_id: str | None = None


class ModuleNode(BaseModel):
    topic: str
    title: str
    icon: str = "📚"
    min_age: int = 10
    max_age: int = 16
    order_index: int
    levels: list[LevelNode]


class CurriculumProposal(BaseModel):
    market_code: str
    modules: list[ModuleNode]


class ValidationReport(BaseModel):
    ok: bool
    missing_backbone: list[str]
    tiers_present: list[int]
    spans_all_tiers: bool
    regressions: list[str]
```

```python
# backend/app/services/market_curriculum/validator.py
from app.services.market_curriculum.backbone import backbone_keys
from app.services.market_curriculum.types import CurriculumProposal, ValidationReport


def _ordered_levels(proposal: CurriculumProposal):
    """All levels flattened in curriculum order (module order, then level order)."""
    out = []
    for module in sorted(proposal.modules, key=lambda m: m.order_index):
        for level in sorted(module.levels, key=lambda lvl: lvl.order_index):
            out.append(level)
    return out


def validate(proposal: CurriculumProposal) -> ValidationReport:
    levels = _ordered_levels(proposal)
    covered: set[str] = set()
    tiers: set[int] = set()
    last_tier_for_key: dict[str, int] = {}
    regressions: list[str] = []

    for level in levels:
        tiers.add(level.complexity_tier)
        for key in level.backbone_keys:
            covered.add(key)
            prev = last_tier_for_key.get(key)
            if prev is not None and level.complexity_tier < prev:
                regressions.append(
                    f"{key} regresses from tier {prev} to {level.complexity_tier}"
                )
            last_tier_for_key[key] = max(level.complexity_tier, prev or 0)

    missing = sorted(backbone_keys() - covered)
    spans_all_tiers = {1, 2, 3}.issubset(tiers)
    ok = not missing and spans_all_tiers and not regressions
    return ValidationReport(
        ok=ok, missing_backbone=missing, tiers_present=sorted(tiers),
        spans_all_tiers=spans_all_tiers, regressions=regressions,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_validator.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_curriculum/types.py backend/app/services/market_curriculum/validator.py backend/tests/test_curriculum_validator.py
git commit -m "feat(curriculum): coverage + progression validator"
```

---

### Task 3: Proposal model + migration

**Files:**
- Create: `backend/app/models/market_curriculum.py`
- Modify: `backend/app/models/__init__.py` (register the model if the project imports models there — check the file; otherwise import where `Market`/`MarketBrief` are imported for metadata)
- Create: `backend/alembic/versions/<rev>_market_curriculum_proposal.py`
- Test: `backend/tests/test_curriculum_proposal_model.py`

**Interfaces:**
- Produces: ORM model `MarketCurriculumProposal` with columns `id` (UUID pk), `market_code` (str(2), indexed), `status` (str, default `"proposed"`), `proposal_json` (JSON), `coverage_json` (JSON), `created_at` (datetime server_default now), `accepted_at` (datetime|None). Valid statuses: `proposed`, `accepted`, `superseded`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_proposal_model.py
import pytest
from sqlalchemy import select
from app.models.market_curriculum import MarketCurriculumProposal

pytestmark = pytest.mark.asyncio(loop_scope="session")

async def test_can_persist_and_read_proposal(db_session):
    row = MarketCurriculumProposal(
        market_code="US", status="proposed",
        proposal_json={"market_code": "US", "modules": []},
        coverage_json={"ok": False, "missing_backbone": ["tax_giving"]},
    )
    db_session.add(row)
    await db_session.flush()
    got = (await db_session.scalars(
        select(MarketCurriculumProposal).where(MarketCurriculumProposal.market_code == "US")
    )).one()
    assert got.status == "proposed"
    assert got.coverage_json["missing_backbone"] == ["tax_giving"]
    assert got.accepted_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_proposal_model.py -q`
Expected: FAIL (import error).

- [ ] **Step 3: Write the model**

```python
# backend/app/models/market_curriculum.py
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MarketCurriculumProposal(Base):
    """A model-proposed, operator-reviewable curriculum tree for one market.
    At most one active (proposed/accepted) row per market; re-designing
    supersedes the prior active row."""
    __tablename__ = "market_curriculum_proposal"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="proposed")
    proposal_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    coverage_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Ensure the model is imported into metadata: check `backend/app/models/__init__.py` and add `from app.models.market_curriculum import MarketCurriculumProposal  # noqa: F401` following the existing pattern there.

- [ ] **Step 4: Generate the chained migration**

Run `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic heads` — confirm a single head; note its revision id. Hand-write the migration (do not autogenerate blindly):

```python
# backend/alembic/versions/<rev>_market_curriculum_proposal.py
"""market curriculum proposal

Revision ID: <rev>
Revises: <previous_head>
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "<rev>"
down_revision = "<previous_head>"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_curriculum_proposal",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("market_code", sa.String(length=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="proposed"),
        sa.Column("proposal_json", sa.JSON(), nullable=False),
        sa.Column("coverage_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_market_curriculum_proposal_market_code",
                    "market_curriculum_proposal", ["market_code"])


def downgrade() -> None:
    op.drop_index("ix_market_curriculum_proposal_market_code",
                  table_name="market_curriculum_proposal")
    op.drop_table("market_curriculum_proposal")
```

- [ ] **Step 5: Apply + run test**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/alembic upgrade head && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_proposal_model.py -q`
Expected: migration applies; PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/market_curriculum.py backend/app/models/__init__.py backend/alembic/versions/*market_curriculum_proposal.py backend/tests/test_curriculum_proposal_model.py
git commit -m "feat(curriculum): market_curriculum_proposal model + migration"
```

---

### Task 4: Curriculum designer (LLM + validate/retry)

**Files:**
- Create: `backend/app/services/market_curriculum/designer.py`
- Test: `backend/tests/test_curriculum_designer.py`

**Interfaces:**
- Consumes: `require_verified_brief` (caller supplies the brief), `get_llm_client`, `extract_json_list`, `validate`, types from Tasks 1–2.
- Produces: `async design_curriculum(market_code: str, brief_json: dict) -> tuple[CurriculumProposal, ValidationReport]`. Raises `CurriculumDesignError` if the LLM output can't be parsed into a `CurriculumProposal` after one retry.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_designer.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.market_curriculum.designer import design_curriculum, CurriculumDesignError

pytestmark = pytest.mark.asyncio(loop_scope="session")

ALL = ["earning_income","spending_budgeting","saving_goals","banking_accounts",
       "borrowing_debt","growing_compound","risk_diversification","safety_scams","tax_giving"]

def _good_tree():
    levels = [{"title": f"L{i}", "order_index": i, "complexity_tier": 1 + i // 3,
               "learning_objective": "o", "concepts": ["c"], "backbone_keys": [k]}
              for i, k in enumerate(ALL)]
    return {"modules": [{"topic": "money", "title": "Money basics", "icon": "💵",
                         "min_age": 10, "max_age": 14, "order_index": 0, "levels": levels}]}

def _patch_llm(*returns):
    client = AsyncMock()
    client.complete = AsyncMock(side_effect=[json.dumps(r) for r in returns])
    return patch("app.services.market_curriculum.designer.get_llm_client", return_value=client), client

async def test_returns_valid_proposal_and_report():
    p_llm, client = _patch_llm(_good_tree())
    with p_llm:
        proposal, report = await design_curriculum("US", {"currency": "USD"})
    assert report.ok and proposal.market_code == "US"
    assert len(proposal.modules[0].levels) == 9
    assert client.complete.await_count == 1

async def test_retries_once_when_a_backbone_key_missing():
    bad = _good_tree(); bad["modules"][0]["levels"] = bad["modules"][0]["levels"][:-1]
    p_llm, client = _patch_llm(bad, _good_tree())
    with p_llm:
        proposal, report = await design_curriculum("US", {"currency": "USD"})
    assert client.complete.await_count == 2 and report.ok

async def test_surfaces_residual_gaps_after_retry():
    bad = _good_tree(); bad["modules"][0]["levels"] = bad["modules"][0]["levels"][:-1]
    p_llm, _ = _patch_llm(bad, bad)
    with p_llm:
        _, report = await design_curriculum("US", {"currency": "USD"})
    assert not report.ok and "tax_giving" in report.missing_backbone

async def test_raises_on_unparseable_output():
    p_llm, _ = _patch_llm("not json", "still not json")
    with p_llm, pytest.raises(CurriculumDesignError):
        await design_curriculum("US", {"currency": "USD"})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_designer.py -q`
Expected: FAIL (import error).

- [ ] **Step 3: Write the designer**

```python
# backend/app/services/market_curriculum/designer.py
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
    try:
        return CurriculumProposal(market_code=market_code, modules=modules or [])
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_designer.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_curriculum/designer.py backend/tests/test_curriculum_designer.py
git commit -m "feat(curriculum): premium-LLM designer with validate/retry"
```

---

### Task 5: Proposal persistence + accept/materialise

**Files:**
- Create: `backend/app/services/market_curriculum/proposal_service.py`
- Test: `backend/tests/test_curriculum_proposal_service.py`

**Interfaces:**
- Consumes: `MarketCurriculumProposal` (Task 3), types (Task 2), `Module`/`Level` models.
- Produces:
  - `async save_proposal(session, proposal: CurriculumProposal, report: ValidationReport) -> MarketCurriculumProposal` — supersedes any prior active row for the market, inserts a new `proposed` row.
  - `async get_active_proposal(session, market_code: str) -> MarketCurriculumProposal | None`.
  - `async accept_proposal(session, row: MarketCurriculumProposal) -> dict` — materialises modules+levels (`has_content` left as-is at market level), writes each created `level_id` back into `proposal_json`, sets `status="accepted"` + `accepted_at`; returns `{"modules": int, "levels": int}`. Idempotency: refuse if already accepted (raise `ValueError`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_proposal_service.py
import pytest
from sqlalchemy import func, select

from app.models.content import Level, Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.types import CurriculumProposal, ModuleNode, LevelNode, ValidationReport
from app.services.market_curriculum.proposal_service import (
    save_proposal, get_active_proposal, accept_proposal,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

def _proposal():
    levels = [LevelNode(title="L0", order_index=0, complexity_tier=1,
                        learning_objective="o", concepts=["a", "b"], backbone_keys=["saving_goals"])]
    mod = ModuleNode(topic="money", title="Money", icon="💵", min_age=10, max_age=14,
                     order_index=0, levels=levels)
    return CurriculumProposal(market_code="US", modules=[mod])

_REPORT = ValidationReport(ok=True, missing_backbone=[], tiers_present=[1,2,3],
                           spans_all_tiers=True, regressions=[])

async def test_save_then_get_active(db_session):
    await save_proposal(db_session, _proposal(), _REPORT)
    row = await get_active_proposal(db_session, "US")
    assert row is not None and row.status == "proposed"

async def test_redesign_supersedes_prior(db_session):
    await save_proposal(db_session, _proposal(), _REPORT)
    await save_proposal(db_session, _proposal(), _REPORT)
    active = (await db_session.scalars(select(MarketCurriculumProposal).where(
        MarketCurriculumProposal.market_code == "US",
        MarketCurriculumProposal.status == "proposed"))).all()
    superseded = (await db_session.scalars(select(MarketCurriculumProposal).where(
        MarketCurriculumProposal.market_code == "US",
        MarketCurriculumProposal.status == "superseded"))).all()
    assert len(active) == 1 and len(superseded) == 1

async def test_accept_materialises_modules_and_levels(db_session):
    row = await save_proposal(db_session, _proposal(), _REPORT)
    result = await accept_proposal(db_session, row)
    assert result == {"modules": 1, "levels": 1}
    mods = (await db_session.scalars(select(Module).where(Module.market_code == "US"))).all()
    assert len(mods) == 1
    n_levels = await db_session.scalar(select(func.count(Level.id)).where(Level.module_id == mods[0].id))
    assert n_levels == 1
    # level_id written back into the stored tree
    assert row.status == "accepted" and row.accepted_at is not None
    assert row.proposal_json["modules"][0]["levels"][0]["level_id"] is not None

async def test_accept_twice_raises(db_session):
    row = await save_proposal(db_session, _proposal(), _REPORT)
    await accept_proposal(db_session, row)
    with pytest.raises(ValueError):
        await accept_proposal(db_session, row)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_proposal_service.py -q`
Expected: FAIL (import error).

- [ ] **Step 3: Write the service**

```python
# backend/app/services/market_curriculum/proposal_service.py
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Level, Module
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.types import CurriculumProposal, ValidationReport

_ACTIVE = ("proposed", "accepted")


async def save_proposal(
    session: AsyncSession, proposal: CurriculumProposal, report: ValidationReport
) -> MarketCurriculumProposal:
    await session.execute(
        update(MarketCurriculumProposal)
        .where(MarketCurriculumProposal.market_code == proposal.market_code,
               MarketCurriculumProposal.status.in_(_ACTIVE))
        .values(status="superseded")
    )
    row = MarketCurriculumProposal(
        market_code=proposal.market_code, status="proposed",
        proposal_json=proposal.model_dump(), coverage_json=report.model_dump(),
    )
    session.add(row)
    await session.flush()
    return row


async def get_active_proposal(
    session: AsyncSession, market_code: str
) -> MarketCurriculumProposal | None:
    return (await session.scalars(
        select(MarketCurriculumProposal)
        .where(MarketCurriculumProposal.market_code == market_code,
               MarketCurriculumProposal.status.in_(_ACTIVE))
        .order_by(MarketCurriculumProposal.created_at.desc())
    )).first()


async def accept_proposal(session: AsyncSession, row: MarketCurriculumProposal) -> dict:
    if row.status == "accepted":
        raise ValueError("proposal already accepted")
    proposal = CurriculumProposal.model_validate(row.proposal_json)
    n_modules = n_levels = 0
    tree = row.proposal_json
    for m_idx, mod_node in enumerate(sorted(proposal.modules, key=lambda m: m.order_index)):
        module = Module(
            topic=mod_node.topic[:30], title=mod_node.title, country_codes=[],
            market_code=proposal.market_code, is_premium=False,
            order_index=mod_node.order_index, icon=mod_node.icon,
            min_age=mod_node.min_age, max_age=mod_node.max_age,
        )
        session.add(module)
        await session.flush()
        n_modules += 1
        for l_idx, lvl_node in enumerate(sorted(mod_node.levels, key=lambda lvl: lvl.order_index)):
            level = Level(
                module_id=module.id, title=lvl_node.title, order_index=lvl_node.order_index,
                is_premium=False, pass_threshold=0.7,
                learning_objectives=[lvl_node.learning_objective],
            )
            session.add(level)
            await session.flush()
            n_levels += 1
            tree["modules"][m_idx]["levels"][l_idx]["level_id"] = str(level.id)
    row.proposal_json = tree
    row.status = "accepted"
    row.accepted_at = datetime.now(timezone.utc)
    # Re-assign the JSON attribute so SQLAlchemy tracks the in-place mutation.
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(row, "proposal_json")
    await session.flush()
    return {"modules": n_modules, "levels": n_levels}
```

> Note: `tree["modules"][m_idx]` relies on `proposal_json["modules"]` already being in `order_index` order — `model_dump()` preserves list order from the proposal, and the designer emits modules/levels in order. The `sorted()` calls above iterate in the same order, so indices line up. If you prefer belt-and-braces, sort `tree["modules"]` and each `levels` list by `order_index` before the loop.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_proposal_service.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/market_curriculum/proposal_service.py backend/tests/test_curriculum_proposal_service.py
git commit -m "feat(curriculum): persist + accept/materialise proposals"
```

---

### Task 6: Native generation — complexity tier + market batch

**Files:**
- Modify: `backend/app/services/admin_content_generation_service.py` (`_system_prompt` native branch; `generate_native_level_lessons` signature; `_generate_one` pass-through)
- Create: `backend/app/services/market_curriculum/native_batch.py`
- Test: `backend/tests/test_curriculum_native_batch.py`

**Interfaces:**
- Consumes: accepted proposal (Task 5), `generate_native_level_lessons`.
- Produces:
  - `generate_native_level_lessons(session, level, *, brief, concepts, types=None, complexity_tier=None)` (added optional `complexity_tier`).
  - `async generate_market_native(session, module, *, brief, proposal_row, include_populated: bool) -> dict` returning `{"levels": [...], "generated": int, "skipped_populated": int, "skipped_has_drafts": int, "skipped_no_concepts": int, "errored": int}`. Reads each level's `concepts` + `complexity_tier` from `proposal_row.proposal_json`. Per-level rollback isolation; skips levels with published lessons OR pending drafts unless `include_populated`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_native_batch.py
import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.models.market_brief import MarketBrief
from app.models.market_curriculum import MarketCurriculumProposal
from app.services.market_curriculum.native_batch import generate_market_native
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

US_BRIEF = {"currency": "USD", "regulators": ["SEC"]}

def _llm():
    client = AsyncMock()
    client.complete = AsyncMock(return_value=json.dumps({"title": "Saving up", "body": "Plan your dollars."}))
    return (client,
            patch("app.services.admin_content_generation_service.get_llm_client", return_value=client),
            patch("app.services.admin_content_generation_service.moderate_output",
                  AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x"))))

async def _seed(db_session, *, with_lesson=False, with_draft=False):
    module = Module(topic="money", title="Money", country_codes=[], market_code="US",
                    is_premium=False, order_index=0, icon="💵", min_age=10, max_age=14)
    db_session.add(module); await db_session.flush()
    level = Level(module_id=module.id, title="L0", order_index=0, is_premium=False, pass_threshold=0.7)
    db_session.add(level); await db_session.flush()
    if with_lesson:
        db_session.add(Lesson(module_id=module.id, level_id=level.id, type="card",
                              xp_reward=0, order_index=0, content_json={"title": "x", "body": "y"}))
    if with_draft:
        db_session.add(LessonDraft(level_id=level.id, type="card",
                                   content_json={"title": "d", "body": "e"}, concept="c",
                                   model_used="t", moderation_safe=True, moderation_category=None))
    proposal = MarketCurriculumProposal(
        market_code="US", status="accepted",
        proposal_json={"market_code": "US", "modules": [{"topic": "money", "title": "Money",
            "icon": "💵", "min_age": 10, "max_age": 14, "order_index": 0, "levels": [
            {"title": "L0", "order_index": 0, "complexity_tier": 2, "learning_objective": "o",
             "concepts": ["saving", "budgeting"], "backbone_keys": ["saving_goals"],
             "level_id": str(level.id)}]}]},
        coverage_json={"ok": True})
    db_session.add(proposal); await db_session.flush()
    return module, level, proposal

async def test_generates_from_proposal_concepts(db_session):
    module, level, proposal = await _seed(db_session)
    brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(brief); await db_session.flush()
    client, p_client, p_mod = _llm()
    with p_client, p_mod:
        summary = await generate_market_native(db_session, module, brief=brief,
                                               proposal_row=proposal, include_populated=False)
    assert summary["generated"] == 1
    n = await db_session.scalar(select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level.id))
    assert n == 2  # one draft per concept
    # the complexity-tier depth instruction reached the prompt
    assert "develop" in client.complete.call_args.kwargs["system_prompt"].lower()

async def test_skips_level_with_pending_drafts(db_session):
    module, level, proposal = await _seed(db_session, with_draft=True)
    brief = MarketBrief(market_code="US", brief_json=US_BRIEF, status="verified")
    db_session.add(brief); await db_session.flush()
    client, p_client, p_mod = _llm()
    with p_client, p_mod:
        summary = await generate_market_native(db_session, module, brief=brief,
                                               proposal_row=proposal, include_populated=False)
    assert summary["generated"] == 0 and summary["skipped_has_drafts"] == 1
    assert client.complete.await_count == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_native_batch.py -q`
Expected: FAIL (import error).

- [ ] **Step 3a: Extend `_system_prompt` native branch + `generate_native_level_lessons`**

In `backend/app/services/admin_content_generation_service.py`, add a tier map and thread `complexity_tier` through. Change the native branch of `_system_prompt` (the `elif brief is not None and source_text is None:` block) to append a depth instruction, and add the param:

```python
_TIER_DEPTH = {
    1: "Write at a FOUNDATIONAL level: first exposure, one concrete idea, very simple.",
    2: "Write at a DEVELOPING level: build on the basics, introduce the mechanics and a trade-off.",
    3: "Write at an ADVANCED level: apply and combine ideas, with nuance and a real decision.",
}
```

```python
def _system_prompt(lesson_type, module, level, *, brief=None, source_text=None,
                   complexity_tier=None):
    ...  # unchanged head
    elif brief is not None and source_text is None:
        prompt += (
            f"\n\nWrite this as a MARKET-NATIVE lesson for the market '{module.market_code}', "
            f"grounded in these verified market facts: {json.dumps(brief, ensure_ascii=False)}. "
            f"Use the market's real products, regulators, currency and age-appropriate local "
            f"examples. This is NOT a UK lesson — do not reference UK-specific products, "
            f"regulators or currency."
        )
        if complexity_tier in _TIER_DEPTH:
            prompt += " " + _TIER_DEPTH[complexity_tier]
    return prompt
```

Thread the param through `_generate_one(..., complexity_tier=None)` into the `_system_prompt(...)` call, and update `generate_native_level_lessons`:

```python
async def generate_native_level_lessons(session, level, *, brief, concepts,
                                        types=None, complexity_tier=None):
    module = await session.get(Module, level.module_id)
    type_cycle = types or ["card", "quiz"]
    result = GenerationResult()
    for i, concept in enumerate(concepts):
        draft = await _generate_one(
            session, level=level, module=module, concept=concept,
            lesson_type=type_cycle[i % len(type_cycle)],
            brief=brief.brief_json, source_text=None, complexity_tier=complexity_tier,
        )
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result
```

- [ ] **Step 3b: Write the batch runner**

```python
# backend/app/services/market_curriculum/native_batch.py
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.services.admin_content_generation_service import generate_native_level_lessons

logger = logging.getLogger(__name__)


def _nodes_by_level_id(proposal_json: dict) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for mod in proposal_json.get("modules", []):
        for lvl in mod.get("levels", []):
            if lvl.get("level_id"):
                out[lvl["level_id"]] = lvl
    return out


async def generate_market_native(
    session: AsyncSession, module: Module, *, brief, proposal_row, include_populated: bool
) -> dict:
    nodes = _nodes_by_level_id(proposal_row.proposal_json)
    target_levels = (await session.execute(
        select(Level.id).where(Level.module_id == module.id).order_by(Level.order_index)
    )).all()
    summary = {"levels": [], "generated": 0, "skipped_populated": 0,
               "skipped_has_drafts": 0, "skipped_no_concepts": 0, "errored": 0}

    for (level_id,) in target_levels:
        entry = {"level_id": str(level_id), "status": "", "created": 0}
        node = nodes.get(str(level_id))
        concepts = (node or {}).get("concepts") or []
        if not concepts:
            entry["status"] = "skipped_no_concepts"
            summary["skipped_no_concepts"] += 1
            summary["levels"].append(entry)
            continue
        if not include_populated:
            lesson_n = await session.scalar(
                select(func.count(Lesson.id)).where(Lesson.level_id == level_id))
            if lesson_n:
                entry["status"] = "skipped_populated"
                summary["skipped_populated"] += 1
                summary["levels"].append(entry)
                continue
            draft_n = await session.scalar(
                select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level_id))
            if draft_n:
                entry["status"] = "skipped_has_drafts"
                summary["skipped_has_drafts"] += 1
                summary["levels"].append(entry)
                continue
        try:
            level = await session.get(Level, level_id)
            result = await generate_native_level_lessons(
                session, level, brief=brief, concepts=concepts,
                complexity_tier=node.get("complexity_tier"),
            )
            entry.update(status="generated", created=len(result.created))
            summary["generated"] += 1
        except Exception as exc:  # noqa: BLE001 — one level must not abort the module
            await session.rollback()
            logger.warning("native batch gen failed for level %s: %s", level_id, exc)
            entry["status"] = "error"
            summary["errored"] += 1
        summary["levels"].append(entry)
    return summary
```

- [ ] **Step 4: Run tests (new + native regression)**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_native_batch.py tests/test_module_batch_generate.py -q`
Expected: PASS (new 2 + existing batch tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/admin_content_generation_service.py backend/app/services/market_curriculum/native_batch.py backend/tests/test_curriculum_native_batch.py
git commit -m "feat(curriculum): native batch generation + complexity-tier depth"
```

---

### Task 7: Admin endpoints + schemas

**Files:**
- Modify: `backend/app/schemas/admin.py` (add curriculum schemas)
- Modify: `backend/app/routers/admin.py` (4 endpoints + imports)
- Test: `backend/tests/test_curriculum_endpoints.py`

**Interfaces:**
- Consumes: designer (Task 4), proposal_service (Task 5), native_batch (Task 6), `require_verified_brief`.
- Produces endpoints:
  - `POST /admin/markets/{market_code}/curriculum/design` → `{ "proposal": {...}, "coverage": {...}, "proposal_id": str }`
  - `GET  /admin/markets/{market_code}/curriculum` → same shape or 404
  - `POST /admin/markets/{market_code}/curriculum/accept` → `{ "modules": int, "levels": int }`
  - `POST /admin/modules/{module_id}/generate-native-batch` → native batch summary dict

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_curriculum_endpoints.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.models.market_brief import MarketBrief
from app.models.market import Market

pytestmark = pytest.mark.asyncio(loop_scope="session")

ALL = ["earning_income","spending_budgeting","saving_goals","banking_accounts",
       "borrowing_debt","growing_compound","risk_diversification","safety_scams","tax_giving"]

def _tree():
    levels = [{"title": f"L{i}", "order_index": i, "complexity_tier": 1 + i // 3,
               "learning_objective": "o", "concepts": ["c"], "backbone_keys": [k]}
              for i, k in enumerate(ALL)]
    return {"modules": [{"topic": "money", "title": "Money", "icon": "💵",
                         "min_age": 10, "max_age": 14, "order_index": 0, "levels": levels}]}

async def _seed_market(db_session):
    db_session.add(Market(code="US", name="United States", currency_code="USD"))
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="verified"))
    await db_session.flush()

async def test_design_then_accept_flow(admin_client, db_session):
    await _seed_market(db_session)
    client = AsyncMock(); client.complete = AsyncMock(return_value=json.dumps(_tree()))
    with patch("app.services.market_curriculum.designer.get_llm_client", return_value=client):
        r = await admin_client.post("/admin/markets/US/curriculum/design")
    assert r.status_code == 200, r.text
    assert r.json()["coverage"]["ok"] is True
    g = await admin_client.get("/admin/markets/US/curriculum")
    assert g.status_code == 200 and len(g.json()["proposal"]["modules"]) == 1
    a = await admin_client.post("/admin/markets/US/curriculum/accept")
    assert a.status_code == 200 and a.json() == {"modules": 1, "levels": 9}

async def test_design_unverified_brief_409(admin_client, db_session):
    db_session.add(Market(code="US", name="United States", currency_code="USD"))
    db_session.add(MarketBrief(market_code="US", brief_json={"currency": "USD"}, status="draft"))
    await db_session.flush()
    r = await admin_client.post("/admin/markets/US/curriculum/design")
    assert r.status_code == 409, r.text

async def test_get_curriculum_404_when_none(admin_client):
    r = await admin_client.get("/admin/markets/ZZ/curriculum")
    assert r.status_code == 404
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_endpoints.py -q`
Expected: FAIL (404 routes).

- [ ] **Step 3a: Add schemas** to `backend/app/schemas/admin.py`

```python
class CurriculumDesignOut(BaseModel):
    proposal_id: str
    proposal: dict
    coverage: dict
```

- [ ] **Step 3b: Add endpoints** to `backend/app/routers/admin.py` (imports at top with the other service imports)

```python
from app.services.market_curriculum.designer import design_curriculum, CurriculumDesignError
from app.services.market_curriculum.proposal_service import (
    save_proposal, get_active_proposal, accept_proposal,
)
from app.services.market_curriculum.native_batch import generate_market_native
```

```python
@router.post("/markets/{market_code}/curriculum/design", response_model=CurriculumDesignOut)
@limiter.limit("5/minute")
async def design_market_curriculum_endpoint(
    request: Request, market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    brief = await require_verified_brief(session, market_code)
    try:
        proposal, report = await design_curriculum(market_code, brief.brief_json)
    except CurriculumDesignError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY,
                            detail="Could not design a curriculum, try again")
    row = await save_proposal(session, proposal, report)
    await session.commit()
    return CurriculumDesignOut(proposal_id=str(row.id), proposal=row.proposal_json,
                               coverage=row.coverage_json)


@router.get("/markets/{market_code}/curriculum", response_model=CurriculumDesignOut)
async def get_market_curriculum_endpoint(
    market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    row = await get_active_proposal(session, market_code)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No curriculum")
    return CurriculumDesignOut(proposal_id=str(row.id), proposal=row.proposal_json,
                               coverage=row.coverage_json)


@router.post("/markets/{market_code}/curriculum/accept")
async def accept_market_curriculum_endpoint(
    market_code: str,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    row = await get_active_proposal(session, market_code)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No curriculum")
    try:
        result = await accept_proposal(session, row)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    await session.commit()
    return result


@router.post("/modules/{module_id}/generate-native-batch")
@limiter.limit("5/minute")
async def generate_native_batch_endpoint(
    request: Request, module_id: uuid.UUID,
    payload: GenerateModuleMarketRequest,
    _admin: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_session),
):
    module = await session.get(Module, module_id)
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    brief = await require_verified_brief(session, module.market_code)
    proposal_row = await get_active_proposal(session, module.market_code)
    if proposal_row is None or proposal_row.status != "accepted":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="No accepted curriculum for this market")
    summary = await generate_market_native(
        session, module, brief=brief, proposal_row=proposal_row,
        include_populated=payload.include_populated)
    await session.commit()
    return summary
```

(Reuse the existing `GenerateModuleMarketRequest{include_populated: bool}` and the `CurriculumDesignOut` import in the schema import block.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_endpoints.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check app tests`
Expected: PASS (3 passed); ruff clean.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/admin.py backend/app/routers/admin.py backend/tests/test_curriculum_endpoints.py
git commit -m "feat(curriculum): admin design/get/accept/native-batch endpoints"
```

---

### Task 8: Frontend — curriculum panel in Market Content

**Files:**
- Modify: `frontend/src/api/admin.ts` (types + hooks)
- Create: `frontend/src/components/admin/CurriculumPanel.tsx`
- Modify: `frontend/src/components/admin/MarketContent.tsx` (render the panel per selected market)
- Modify: `frontend/src/locales/en/admin.json` (`marketContent.curriculum.*`)
- Test: `frontend/src/components/admin/__tests__/CurriculumPanel.test.tsx`

**Interfaces:**
- Consumes: endpoints from Task 7.
- Produces in `admin.ts`:
  - types `CurriculumLevelNode`, `CurriculumModuleNode`, `CurriculumCoverage { ok:boolean; missing_backbone:string[]; spans_all_tiers:boolean; regressions:string[] }`, `CurriculumDesign { proposal_id:string; proposal:{ market_code:string; modules:CurriculumModuleNode[] }; coverage:CurriculumCoverage }`.
  - hooks `useCurriculum(marketCode)` (GET, 404→null), `useDesignCurriculum()` (POST design), `useAcceptCurriculum()` (POST accept), each invalidating `['admin','curriculum',marketCode]` and `['admin','levels']`/`['admin','modules']` as relevant.

- [ ] **Step 1: Write the failing component test**

```tsx
// frontend/src/components/admin/__tests__/CurriculumPanel.test.tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { axe } from 'vitest-axe';
import { describe, it, expect, vi } from 'vitest';
import CurriculumPanel from '../CurriculumPanel';

vi.mock('@/api/admin', async (orig) => ({
  ...(await orig<typeof import('@/api/admin')>()),
  useCurriculum: () => ({ data: {
    proposal_id: 'p1',
    proposal: { market_code: 'US', modules: [
      { topic: 'money', title: 'Money basics', icon: '💵', min_age: 10, max_age: 14,
        order_index: 0, levels: [
          { title: 'L0', order_index: 0, complexity_tier: 1, learning_objective: 'o',
            concepts: ['c'], backbone_keys: ['saving_goals'] }] }] },
    coverage: { ok: false, missing_backbone: ['tax_giving'], spans_all_tiers: true, regressions: [] },
  }, isLoading: false }),
  useDesignCurriculum: () => ({ mutate: vi.fn(), isPending: false }),
  useAcceptCurriculum: () => ({ mutate: vi.fn(), isPending: false }),
}));

function wrap(ui: React.ReactNode) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe('CurriculumPanel', () => {
  it('shows modules, a tier badge and a coverage gap chip', () => {
    render(wrap(<CurriculumPanel marketCode="US" />));
    expect(screen.getByText('Money basics')).toBeInTheDocument();
    expect(screen.getByText(/tax_giving/)).toBeInTheDocument();      // gap chip
    expect(screen.getByText(/foundational/i)).toBeInTheDocument();   // tier badge
  });

  it('has no axe violations', async () => {
    const { container } = render(wrap(<CurriculumPanel marketCode="US" />));
    expect(await axe(container)).toHaveNoViolations();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/CurriculumPanel.test.tsx`
Expected: FAIL (no component).

- [ ] **Step 3a: Add API types + hooks** to `frontend/src/api/admin.ts` (follow the existing hook patterns — `adminFetch`, `useQuery`, `useMutation`, `qc.invalidateQueries`):

```ts
export type CurriculumLevelNode = {
  title: string; order_index: number; complexity_tier: number;
  learning_objective: string; concepts: string[]; backbone_keys: string[]; level_id?: string | null;
};
export type CurriculumModuleNode = {
  topic: string; title: string; icon: string; min_age: number; max_age: number;
  order_index: number; levels: CurriculumLevelNode[];
};
export type CurriculumCoverage = {
  ok: boolean; missing_backbone: string[]; spans_all_tiers: boolean; regressions: string[];
};
export type CurriculumDesign = {
  proposal_id: string;
  proposal: { market_code: string; modules: CurriculumModuleNode[] };
  coverage: CurriculumCoverage;
};

export function useCurriculum(marketCode: string) {
  return useQuery({
    queryKey: ['admin', 'curriculum', marketCode],
    queryFn: () => adminFetch<CurriculumDesign | null>(
      `/admin/markets/${marketCode}/curriculum`, {}, { allow404: true }),
    enabled: !!marketCode,
  });
}
export function useDesignCurriculum(marketCode: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<CurriculumDesign>(
      `/admin/markets/${marketCode}/curriculum/design`, { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin', 'curriculum', marketCode] }),
  });
}
export function useAcceptCurriculum(marketCode: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => adminFetch<{ modules: number; levels: number }>(
      `/admin/markets/${marketCode}/curriculum/accept`, { method: 'POST' }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin', 'curriculum', marketCode] });
      qc.invalidateQueries({ queryKey: ['admin', 'modules'] });
      qc.invalidateQueries({ queryKey: ['admin', 'levels'] });
    },
  });
}
```

> If `adminFetch` has no `allow404` option, add a minimal one (return `null` on 404) following its existing signature; otherwise wrap the GET in a try/catch that maps a 404 `ApiError` to `null`.

- [ ] **Step 3b: Write `CurriculumPanel.tsx`** — renders Design button when no curriculum; otherwise the module/level tree with tier badges (`foundational`/`developing`/`advanced` via i18n) and coverage chips (✓ covered keys, ⚠ each `missing_backbone` key + any `regressions`), plus **Accept** and **Regenerate** buttons. Use existing tokens (`brand-*`, `success-*`, `danger-*`); `role="status"` on async results. Keep copy in `marketContent.curriculum.*`.

- [ ] **Step 3c: Mount the panel** in `MarketContent.tsx` above the module list for the selected market: `<CurriculumPanel marketCode={market.code} />`.

- [ ] **Step 3d: Add i18n** keys under `marketContent.curriculum` in `frontend/src/locales/en/admin.json`: `design`, `regenerate`, `accept`, `accepted`, `designing`, `coverageOk`, `coverageGap` (`"Missing: {{key}}"`), `tier1` (`"foundational"`), `tier2` (`"developing"`), `tier3` (`"advanced"`), `noCurriculum`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/CurriculumPanel.test.tsx && npx tsc -b`
Expected: PASS (2 tests); tsc clean.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/admin.ts frontend/src/components/admin/CurriculumPanel.tsx frontend/src/components/admin/MarketContent.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/CurriculumPanel.test.tsx
git commit -m "feat(curriculum): Market Content curriculum panel (design/accept + coverage)"
```

---

### Task 9: Frontend — native generation wiring + inline draft review (#1 fix)

**Files:**
- Modify: `frontend/src/api/admin.ts` (`generateModuleLessons` → point the market batch at `/generate-native-batch`; add `skipped_no_concepts` to `ModuleBatchResult`)
- Modify: `frontend/src/components/admin/MarketContent.tsx` (generate buttons call native batch; level row "Review N drafts" opens an **inline** review panel instead of linking away; retire the from-GB "Generate (from GB)" affordances)
- Create: `frontend/src/components/admin/InlineDraftReview.tsx` (wraps the existing `LessonDraftReview` body in an expandable panel scoped to a level, with approve/publish staying in place)
- Modify: `frontend/src/locales/en/admin.json` (`marketContent.review.*`)
- Test: `frontend/src/components/admin/__tests__/MarketContent.test.tsx` (update + add inline-review assertion)

**Interfaces:**
- Consumes: `useApproveDrafts` / approve-replace hooks (existing), `generate-native-batch` (Task 7).
- Produces: `ModuleBatchResult` gains `skipped_no_concepts: number` (fold into the skipped total alongside `skipped_populated`/`skipped_has_drafts`/`skipped_no_source`). The market batch helper posts to `/admin/modules/{id}/generate-native-batch`.

- [ ] **Step 1: Write/refresh the failing test**

In `MarketContent.test.tsx`, add `skipped_no_concepts: 0` to the `ModuleBatchResult` fixture type + `emptyBatch`, and add:

```tsx
it('opens inline draft review in place instead of navigating away', async () => {
  // a level with draft_count > 0 renders a "Review N drafts" control that, when
  // clicked, reveals the inline review panel within Market Content (no router navigation).
  // Assert the review panel heading appears after click and no <a href=.../lessons> is used.
});
```

Fill the test body using the existing render helpers in that file (mirror the current "shows a 'Review N drafts' link" test, but assert a button that toggles an in-place panel — `screen.getByRole('button', { name: /review/i })`, click, then `getByText` the review heading — and assert there is **no** anchor to `/lessons`).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/admin/__tests__/MarketContent.test.tsx`
Expected: FAIL (inline panel not implemented).

- [ ] **Step 3a:** Add `skipped_no_concepts: number` to `ModuleBatchResult` in `admin.ts`; repoint `generateModuleLessons(moduleId, include_populated)` (and the `useGenerateModuleLessons` hook if separate) to `POST /admin/modules/${moduleId}/generate-native-batch`. Update the two skipped-total sums in `MarketContent.tsx` to include `skipped_no_concepts`.

- [ ] **Step 3b:** Create `InlineDraftReview.tsx`: a small wrapper that, given `levelId`, renders the existing `LessonDraftReview` (reused) inside a collapsible panel; the level row in `MarketContent.tsx` toggles it via local state (`expandedLevelId`). Remove the `<Link to={.../lessons}>` from `LevelGenerator` and replace it with a `<button>` that toggles the inline panel; keep the `draftCount > 0` guard and the `reviewDrafts` label.

- [ ] **Step 3c:** Remove/retire the from-GB market affordances in `MarketContent.tsx` (the per-level "Generate lessons (from GB)" trigger and any "Generate all (from GB)" wording) in favour of the native batch buttons. Leave the underlying `/generate-market` endpoint in place (no backend deletion) but unwired from this UI.

- [ ] **Step 3d:** Add `marketContent.review.*` i18n keys (`heading`, `close`).

- [ ] **Step 4: Run the frontend gates**

Run: `cd frontend && npx vitest run src/components/admin && npx tsc -b && npm run lint`
Expected: PASS; tsc clean; lint 0 errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/admin.ts frontend/src/components/admin/InlineDraftReview.tsx frontend/src/components/admin/MarketContent.tsx frontend/src/locales/en/admin.json frontend/src/components/admin/__tests__/MarketContent.test.tsx
git commit -m "feat(curriculum): native batch buttons + inline draft review in Market Content"
```

---

### Task 10: Full verification + US pilot + docs

**Files:**
- Modify: `docs/superpowers/PROGRESS.md` (record the engine, live state)
- Modify: `AGENTS.md` / `invest-ed/AGENTS.md` / `.cursor/rules/` only if the market-content workflow description references the retired from-GB path (keep tool docs consistent)

- [ ] **Step 1: Backend full slice + lint**

Run: `cd backend && /Users/leeashmore/Local\ Repo/.venv/bin/pytest tests/test_curriculum_*.py tests/test_module_batch_generate.py tests/test_approve_drafts.py -q && /Users/leeashmore/Local\ Repo/.venv/bin/ruff check .`
Expected: all PASS; ruff clean.

- [ ] **Step 2: Frontend full gates**

Run: `cd frontend && npx tsc -b && npm run lint && npm run test && npm run build`
Expected: tsc clean; lint 0 errors; tests pass; build OK. (No `cap sync ios` needed — admin-web only.)

- [ ] **Step 3: Promote to `testing`, green CI, then staging→main** per the standing flow; this includes a **migration** (Task 3) — ask the user before the production migration whether to snapshot first. Vercel prod deploy + alias `app.investikid.ai`.

- [ ] **Step 4: US pilot (operator-run, with you)** — in the Market Content tab for US: **Design curriculum** → review coverage chips → **Accept** → **Generate all** (native) → **Review drafts** inline → **Publish**. Confirm the content is genuinely distinct from UK and reads better. Discard the old US currency-swap drafts as part of this (they sit on the retired modules; remove those modules or leave them unpublished per your call).

- [ ] **Step 5: Update `PROGRESS.md`** (standing rule) with the engine, the migration id, and the pilot outcome; commit and sync to `main`.

- [ ] **Step 6: Roll out** to AU/CA/IE/ES/FR/DE/HK/SG, then **GB last (drafts-only)** — regenerate, review, approve a replace of the live authored lessons only on your explicit sign-off.

---

## Self-Review notes

- **Spec coverage:** designer (T4), backbone (T1) incl. tax_giving, progressive-complexity tiers + validator (T2) + generation depth (T6), proposal persistence/review (T3/T5/T8), native batch retiring from-GB (T6/T9), inline review #1 fix (T9), UK drafts-only + US pilot + rollout (T10). All spec sections map to a task.
- **Type consistency:** `CurriculumProposal`/`ModuleNode`/`LevelNode`/`ValidationReport` defined in T2 and reused verbatim in T4/T5; `complexity_tier` threaded T4→T5(JSON)→T6(generation); `skipped_has_drafts`/`skipped_no_concepts` consistent between T6 batch and T9 frontend totals; `CurriculumDesign`/coverage shapes match T7 endpoint output and T8 frontend types.
- **Migration:** single new table, chained off the live head (T3) — flagged for snapshot before prod.
