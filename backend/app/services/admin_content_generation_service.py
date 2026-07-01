from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.concept import Concept
from app.models.content import Lesson, Level, Module
from app.models.lesson_draft import LessonDraft
from app.schemas.admin import validate_lesson_content_json
from app.services import llm_usage
from app.services.llm_client import get_llm_client, get_model_name
from app.services.llm_json import extract_json_list
from app.services.moderation import moderate_output

logger = logging.getLogger(__name__)

_TIER_DEPTH = {
    1: "Write at a FOUNDATIONAL level: first exposure, one concrete idea, very simple.",
    2: "Write at a DEVELOPING level: build on the basics, introduce the mechanics and a trade-off.",
    3: "Write at an ADVANCED level: apply and combine ideas, with nuance and a real decision.",
}

_SCHEMA_HINT = {
    "card": '{"title": str, "body": str, "concept_slug": str}',
    "quiz": (
        '{"question": str, "choices": [str, str, ...(2-5)], '
        '"answer_index": int, "explanation": str, "concept_slug": str}'
    ),
    "scenario": (
        '{"prompt": str, "choices": [{"label": str, "outcome": str}, ...(>=2)], '
        '"correct_index": int, "concept_slug": str}'
    ),
}

# Lessons generated per level, by complexity tier (1 foundational … 3 advanced).
# This is the EXACT lesson count per level; each concept yields a teach-card +
# practice-quiz pair, so a level needs ~ceil(target/2) concepts (the designer is
# asked for that many; the generator wraps concepts if a level returns fewer).
LESSONS_PER_TIER: dict[int, int] = {1: 10, 2: 15, 3: 20}


def target_lessons_for_tier(tier: int | None) -> int:
    """Exact number of lessons to generate for a level of the given tier."""
    return LESSONS_PER_TIER.get(tier or 0, LESSONS_PER_TIER[2])


# Markets that use American English spelling/idioms; everything else defaults to
# British/Commonwealth English (GB/IE/AU/NZ/HK/SG). Keeps gpt-5-mini from leaking
# "mum/neighbour/paper round" into US content (and vice-versa).
_AMERICAN_ENGLISH_MARKETS = {"US", "CA"}


def _market_english(market_code: str | None) -> str:
    if (market_code or "").upper() in _AMERICAN_ENGLISH_MARKETS:
        return ("American English spelling and idioms (mom, neighbor, color, check, "
                "route, soccer) — do NOT use British forms like mum, neighbour, colour, "
                "cheque, 'paper round' or 'maths'")
    return ("the market's own British/Commonwealth English spelling and idioms "
            "(e.g. mum, neighbour, colour) — do NOT use American forms")

# Concise, kid-readable style for ALL generated lessons. Pitched at UK years 8-10
# (confident teen reader), easy to read on a phone; depth-on-demand lives in
# Coach Penny, not the card.
_CONCISION_RULES = (
    "\n\nSTYLE — pitch the language at UK school years 8-10 (a confident teen reader, "
    "roughly ages 12-15): clear and direct, never childish or patronising, and easy to "
    "read on a phone:\n"
    "- For a 'card', the body MUST be 45-65 words: 3-5 sentences, ONE key idea, plain "
    "prose (do NOT use long bullet lists).\n"
    "- For 'quiz' and 'scenario', keep each explanation/outcome to 1-2 sentences "
    "(max ~30 words).\n"
    "- Short, clear sentences in plain language — but do NOT talk down to them or pad "
    "with filler. Keep a warm, encouraging tone.\n"
    "- Avoid acronyms and regulatory jargon (e.g. FSCS, ISA product names, 'parental "
    "consent and ID checks') UNLESS the lesson is specifically about that term — then "
    "explain it in one plain phrase.\n"
    "- Teach the core idea only. Learners can ask Coach Penny for more detail, so do NOT "
    "try to cover everything."
)


@dataclass
class GenerationResult:
    created: list[LessonDraft] = field(default_factory=list)
    skipped: int = 0


def _system_prompt(
    lesson_type: str,
    module: Module,
    level: Level,
    *,
    brief: dict | None = None,
    source_text: str | None = None,
    complexity_tier: int | None = None,
    avoid: list[str] | None = None,
    concept_slugs: list[str] | None = None,
) -> str:
    age = f"ages {module.min_age}-{module.max_age}" if module.min_age else "children 8-16"
    slug_hint = ""
    if concept_slugs:
        slug_hint = (
            f" For 'concept_slug', choose the single most relevant slug from this "
            f"taxonomy list (use exact spelling): {concept_slugs}."
        )
    prompt = (
        f"You write a single financial-education {lesson_type} lesson for {age} on the topic "
        f"'{module.topic}' (module '{module.title}', '{level.title}'). Keep it simple, encouraging, "
        f"factual, and age-appropriate. Never give personalised financial advice. "
        f"Use a fresh, concrete everyday scenario with a varied character name (rotate genders, "
        f"backgrounds and situations — do NOT default to one go-to name or example). "
        f"Respond with ONLY a JSON object matching exactly: {_SCHEMA_HINT[lesson_type]}"
        f"{slug_hint}"
        f"{_CONCISION_RULES}"
    )
    if avoid:
        prompt += (
            "\n\nVARIETY — this is one of several lessons in the same level. To avoid "
            "repetition, your lesson MUST use a DISTINCTLY different scenario, a different "
            "person's name, and a different angle from the ones ALREADY used below. Never "
            "reuse the same character, job, amount or situation:\n- " + "\n- ".join(avoid)
        )
    if brief is not None and source_text is not None:
        prompt += (
            f"\n\nADAPT the following GB (United Kingdom) lesson's concept into the target "
            f"market '{module.market_code}' using these verified market facts: "
            f"{json.dumps(brief, ensure_ascii=False)}. "
            f"Replace UK products, regulators, currency and examples with the market's real "
            f"equivalents from the facts above (e.g. ISA → the local tax-advantaged account, "
            f"FCA → the local regulator, £ → the local currency). Keep the learning objective, "
            f"structure and age level identical. Do not copy GB-specific names, regulators or "
            f"currency. Source lesson: {source_text}"
        )
    elif brief is not None and source_text is None:
        prompt += (
            f"\n\nWrite this as a MARKET-NATIVE lesson for the market '{module.market_code}', "
            f"grounded in these verified market facts: {json.dumps(brief, ensure_ascii=False)}. "
            f"Use the market's real products, regulators, currency and age-appropriate local "
            f"examples. This is NOT a UK lesson — do not reference UK-specific products, "
            f"regulators or currency. "
            f"Write in {_market_english(module.market_code)}."
        )
        if complexity_tier in _TIER_DEPTH:
            prompt += " " + _TIER_DEPTH[complexity_tier]
    return prompt


# Mini-batch size for grouped market-adaptation generation: each type-group of
# source lessons is chunked into batches of this size, one LLM call per batch
# (instead of one call per lesson) -- see generate_market_level_lessons.
_MARKET_ADAPT_BATCH_SIZE = 5


def _batch_system_prompt(
    lesson_type: str,
    module: Module,
    level: Level,
    *,
    brief: dict,
    items: list[tuple[str, str]],
) -> str:
    """Batched variant of the ``brief`` + ``source_text`` branch of ``_system_prompt``:
    adapts MULTIPLE GB source lessons of the SAME ``lesson_type`` into the target
    market in a single call, each grounded in its own source lesson's text but all
    sharing the same market ``brief``. ``items`` is a list of (source_lesson_id,
    source_text) pairs -- one per lesson to adapt in this mini-batch.
    """
    age = f"ages {module.min_age}-{module.max_age}" if module.min_age else "children 8-16"
    sources_block = "\n".join(
        f'- source_lesson_id "{lesson_id}": {source_text}'
        for lesson_id, source_text in items
    )
    item_schema = _SCHEMA_HINT[lesson_type][:-1] + ', "source_lesson_id": str}'
    prompt = (
        f"You adapt {len(items)} financial-education {lesson_type} lessons for {age} on the "
        f"topic '{module.topic}' (module '{module.title}', '{level.title}') from GB (United "
        f"Kingdom) source lessons into the target market '{module.market_code}', using these "
        f"verified market facts shared by ALL of them: {json.dumps(brief, ensure_ascii=False)}. "
        f"Replace UK products, regulators, currency and examples with the market's real "
        f"equivalents from the facts above (e.g. ISA → the local tax-advantaged account, "
        f"FCA → the local regulator, £ → the local currency). Keep each lesson's learning "
        f"objective, structure and age level identical to its own source. Do not copy "
        f"GB-specific names, regulators or currency. Keep it simple, encouraging, factual, and "
        f"age-appropriate; never give personalised financial advice. Use a fresh, concrete "
        f"everyday scenario per lesson with a varied character name (rotate genders, "
        f"backgrounds and situations across the lessons — do NOT reuse the same character "
        f"across them).\n\n"
        f"Here are the {len(items)} GB source lessons to adapt, each tagged with its own "
        f"source_lesson_id:\n{sources_block}\n\n"
        f"Respond with ONLY a JSON array of exactly {len(items)} objects, one per source "
        f"lesson above (any order), each matching exactly: {item_schema} -- the "
        f"'source_lesson_id' in each object MUST exactly match the source_lesson_id it was "
        f"adapted from, so the results can be correlated back to their source."
        f"{_CONCISION_RULES}"
    )
    return prompt


def _concat_text(parsed: dict) -> str:
    parts: list[str] = []
    for key in ("title", "body", "question", "explanation", "prompt"):
        if isinstance(parsed.get(key), str):
            parts.append(parsed[key])
    for ch in parsed.get("choices", []) or []:
        if isinstance(ch, str):
            parts.append(ch)
        elif isinstance(ch, dict):
            parts.extend(str(ch.get(k, "")) for k in ("label", "outcome"))
    return "\n".join(parts)


async def _fetch_all_concept_slugs(session: AsyncSession) -> list[str]:
    """Return ALL concept slugs from the full taxonomy, ordered by topic then order_index.

    The full taxonomy is passed to the LLM so it can emit a taxonomy-valid slug
    regardless of what free-form topic the module carries.  Slug uniqueness is
    guaranteed by the UNIQUE constraint on Concept.slug.
    """
    rows = (
        await session.scalars(
            select(Concept.slug).order_by(Concept.topic, Concept.order_index)
        )
    ).all()
    return list(rows)


async def _persist_draft_from_parsed(session, *, level, lesson_type: str, concept: str,
                                     parsed: dict) -> LessonDraft:
    """Validate (already done by caller) + moderate a single parsed LLM lesson dict,
    then persist it as a LessonDraft. Shared by the single-lesson (_generate_one) and
    batched (_generate_batch) generation paths so every persisted draft gets the SAME
    per-item moderation + audit-log treatment, one lesson at a time.
    """
    # Extract the concept_slug the LLM emitted (may be absent or invalid — stored
    # as-is; resolved to concept_id at approval time via the concept mapper).
    emitted_slug = parsed.pop("concept_slug", None)
    if isinstance(emitted_slug, str):
        emitted_slug = emitted_slug.strip() or None
    else:
        emitted_slug = None
    mod = await moderate_output(_concat_text(parsed), surface="lesson")
    draft = LessonDraft(
        level_id=level.id, type=lesson_type, content_json=parsed, concept=concept,
        model_used=get_model_name("authoring"),
        moderation_safe=mod.safe, moderation_category=mod.category,
        concept_slug=emitted_slug,
    )
    session.add(draft)
    if not mod.safe:
        session.add(AuditLog(
            user_id=None,
            event_type="moderation_block",
            metadata_json={"surface": "lesson", "category": mod.category},
        ))
    await session.flush()
    return draft


@llm_usage.surface("admin_content_gen")
async def _generate_one(session, *, level, module, concept: str, lesson_type: str,
                        brief: dict | None = None, source_text: str | None = None,
                        complexity_tier: int | None = None, avoid: list[str] | None = None,
                        concept_slugs: list[str] | None = None):
    client = get_llm_client("authoring")
    system = _system_prompt(lesson_type, module, level, brief=brief, source_text=source_text,
                            complexity_tier=complexity_tier, avoid=avoid,
                            concept_slugs=concept_slugs)
    user = f"Create a {lesson_type} lesson teaching: {concept}."
    parsed = None
    for attempt in range(2):
        raw = await client.complete(
            system_prompt=system,
            messages=[{"role": "user", "content": user}],
            temperature=0.4, max_tokens=700, response_format="json",
        )
        try:
            parsed = json.loads(raw)
            validate_lesson_content_json(lesson_type, parsed)
            break
        except (json.JSONDecodeError, ValueError, TypeError):
            parsed = None
            if attempt == 1:
                return None
    return await _persist_draft_from_parsed(
        session, level=level, lesson_type=lesson_type, concept=concept, parsed=parsed,
    )


async def regenerate_draft(session: AsyncSession, draft: LessonDraft) -> LessonDraft | None:
    level = await session.get(Level, draft.level_id)
    module = await session.get(Module, level.module_id)
    fresh = await _generate_one(session, level=level, module=module, concept=draft.concept,
                                lesson_type=draft.type)
    if fresh is None:
        return None
    draft.content_json = fresh.content_json
    draft.moderation_safe = fresh.moderation_safe
    draft.moderation_category = fresh.moderation_category
    draft.model_used = fresh.model_used
    await session.delete(fresh)
    await session.commit()
    return draft


async def generate_level_lessons(session: AsyncSession, level, *, concept: str, count: int,
                                 types: list[str]) -> GenerationResult:
    module = await session.get(Module, level.module_id)
    result = GenerationResult()
    for i in range(count):
        lesson_type = types[i % len(types)]
        draft = await _generate_one(session, level=level, module=module, concept=concept,
                                    lesson_type=lesson_type)
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
    await session.commit()
    return result


async def generate_native_level_lessons(session: AsyncSession, level, *, brief, concepts,
                                        types: list[str] | None = None,
                                        complexity_tier: int | None = None,
                                        target_count: int | None = None) -> GenerationResult:
    """Generate market-NATIVE lessons (brief-grounded, no GB source) for ``level``.

    ``target_count`` controls how many lessons to produce:
    - ``None`` (default, ad-hoc per-level generation): exactly one lesson per
      concept, the lesson type alternating per concept.
    - an int (curriculum batch with tiered depth): exactly ``target_count`` lessons
      by round-robin over (concept, type) — concept0-card, concept0-quiz,
      concept1-card, … so each concept gets a teach-card + practice-quiz pair;
      concepts wrap (% len) if the level returned fewer than ceil(target/n_types).
    """
    module = await session.get(Module, level.module_id)
    # Rotate three formats (teach card → practice quiz → decision scenario) for
    # variety; the ad-hoc path keeps the caller's types or the card/quiz default.
    type_cycle = types or (["card", "quiz", "scenario"] if target_count else ["card", "quiz"])
    result = GenerationResult()
    if not concepts:
        await session.commit()
        return result
    n_types = len(type_cycle)
    if target_count is None:
        pairs = [(concepts[i], type_cycle[i % n_types]) for i in range(len(concepts))]
    else:
        pairs = [(concepts[(n // n_types) % len(concepts)], type_cycle[n % n_types])
                 for n in range(target_count)]
    # Fetch ALL concept slugs (full taxonomy) so the generator can guide the LLM
    # to emit a taxonomy-valid slug regardless of the module's free-form topic.
    # Slug is globally unique, so this is safe and matches how approval resolves it.
    slugs_for_topic = await _fetch_all_concept_slugs(session)
    # Sibling-aware: tell each lesson which scenarios/characters are already used in
    # this level so it picks a distinctly different one (kills the "every question
    # is the same Maya-walks-the-dog" repetition).
    avoid: list[str] = []
    for concept, lesson_type in pairs:
        draft = await _generate_one(
            session, level=level, module=module, concept=concept,
            lesson_type=lesson_type,
            brief=brief.brief_json, source_text=None, complexity_tier=complexity_tier,
            avoid=avoid[-12:],
            concept_slugs=slugs_for_topic or None,
        )
        if draft is None:
            result.skipped += 1
        else:
            result.created.append(draft)
            cj = draft.content_json or {}
            head = cj.get("title") or cj.get("question") or cj.get("prompt") or ""
            avoid.append(f"{concept}: {str(head)[:80]}")
    await session.commit()
    return result


def _lesson_concept(lesson: Lesson) -> str:
    """Derive a short concept string from a source lesson's content."""
    content = lesson.content_json or {}
    for key in ("title", "question", "prompt"):
        value = content.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:200]
    return lesson.type


@llm_usage.surface("admin_content_gen")
async def _generate_batch(
    session, *, level, module, brief: dict, lesson_type: str, batch: list[Lesson],
) -> GenerationResult:
    """Adapt one mini-batch of SAME-type source lessons into the target market with
    ONE LLM call, expecting a JSON array of ``len(batch)`` adapted-lesson objects
    each tagged with its source lesson's id for correlation.

    Resilience:
    - If the whole call throws or the response can't be parsed at all, every
      lesson in ``batch`` counts as skipped.
    - Each extracted item is independently validated + moderated (via
      ``_persist_draft_from_parsed``, the same per-item path ``_generate_one``
      uses); a missing/malformed/invalid item skips only that one lesson without
      losing its batch-mates.
    """
    result = GenerationResult()
    items = [(str(src.id), _concat_text(src.content_json or {})) for src in batch]
    client = get_llm_client("authoring")
    system = _batch_system_prompt(lesson_type, module, level, brief=brief, items=items)
    user = f"Adapt these {len(batch)} {lesson_type} lessons."
    # Retry once on a whole-batch call/parse failure (mirrors _generate_one's 2
    # attempts) so a single transient bad completion doesn't skip up to `len(batch)`
    # lessons. A second failure skips the whole mini-batch (never aborts others).
    candidates = None
    for attempt in range(2):
        try:
            raw = await client.complete(
                system_prompt=system,
                messages=[{"role": "user", "content": user}],
                temperature=0.4, max_tokens=700 * len(batch), response_format="json",
            )
            candidates = extract_json_list(json.loads(raw))
            break
        except Exception:  # noqa: BLE001 — the whole mini-batch's LLM call/parse must
            # never abort other mini-batches; log so a real outage is still visible.
            logger.warning(
                "market lesson-adaptation batch failed for level %s type=%s (n=%d, attempt=%d)",
                level.id, lesson_type, len(batch), attempt + 1, exc_info=True,
            )
            if attempt == 1:
                result.skipped += len(batch)
                return result
    by_id = {str(src.id): src for src in batch}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        src_id = candidate.get("source_lesson_id")
        src = by_id.pop(src_id, None) if isinstance(src_id, str) else None
        if src is None:
            continue  # unmatched/duplicate id — ignore rather than mis-attribute
        parsed = {k: v for k, v in candidate.items() if k != "source_lesson_id"}
        try:
            validate_lesson_content_json(lesson_type, parsed)
        except (ValueError, TypeError):
            result.skipped += 1
            continue
        draft = await _persist_draft_from_parsed(
            session, level=level, lesson_type=lesson_type,
            concept=_lesson_concept(src), parsed=parsed,
        )
        result.created.append(draft)
    # Any source lesson left in `by_id` had no valid matching entry in the response.
    result.skipped += len(by_id)
    return result


def _chunked(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)]


async def generate_market_level_lessons(session: AsyncSession, target_level, *,
                                        source_level, brief) -> GenerationResult:
    """Adapt every lesson under ``source_level`` (GB) into ``target_level``'s market.

    Each generated draft is grounded in the verified ``brief`` and the GB lesson's
    text. The caller is responsible for passing a verified brief.

    LLM-generatable source lessons are grouped by ``type`` (each type has its own
    output schema) then chunked into mini-batches of ``_MARKET_ADAPT_BATCH_SIZE``;
    ONE LLM call adapts an entire mini-batch, instead of one call per lesson. Every
    _generate_one call this replaces was already fully independent (grounded only
    in its own source lesson + the shared brief), so batching changes nothing about
    what's asked for -- only how many calls it takes.
    """
    target_module = await session.get(Module, target_level.module_id)
    source_lessons = (await session.scalars(
        select(Lesson).where(Lesson.level_id == source_level.id).order_by(Lesson.order_index)
    )).all()
    result = GenerationResult()
    by_type: dict[str, list[Lesson]] = {}
    for src in source_lessons:
        # Only card/quiz/scenario are LLM-generatable. A GB level can also hold a
        # `video` lesson (curated YouTube) — skip those rather than crash trying
        # to build a prompt schema for a type we can't generate.
        if src.type not in _SCHEMA_HINT:
            result.skipped += 1
            continue
        by_type.setdefault(src.type, []).append(src)

    for lesson_type, lessons in by_type.items():
        for batch in _chunked(lessons, _MARKET_ADAPT_BATCH_SIZE):
            batch_result = await _generate_batch(
                session, level=target_level, module=target_module,
                brief=brief.brief_json, lesson_type=lesson_type, batch=batch,
            )
            result.created.extend(batch_result.created)
            result.skipped += batch_result.skipped
    await session.commit()
    return result


async def _gb_source_module(session, target_module: Module) -> Module | None:
    """Resolve the GB source module for a market module by the fields the scaffold
    preserves (topic + order_index). Returns None unless exactly one match."""
    rows = (await session.scalars(
        select(Module).where(
            Module.market_code == "GB",
            Module.topic == target_module.topic,
            Module.order_index == target_module.order_index,
        )
    )).all()
    return rows[0] if len(rows) == 1 else None


async def generate_module_market_lessons(
    session, target_module, *, brief, include_populated: bool
) -> dict:
    """Generate market drafts for every level in ``target_module``, resolving each
    level's GB source by order_index. Skips levels that already have lessons unless
    ``include_populated``. Best-effort per level (one failure never aborts the rest)."""
    gb_module = await _gb_source_module(session, target_module)
    # Capture identity as plain values up front: a per-level rollback (below)
    # expires ORM objects, so the loop must NOT touch attributes of cached
    # Level instances afterward — it re-`session.get`s fresh objects instead.
    target_levels = (await session.execute(
        select(Level.id, Level.order_index)
        .where(Level.module_id == target_module.id).order_by(Level.order_index)
    )).all()
    gb_by_order: dict[int, list] = {}
    if gb_module is not None:
        for src_id, src_order in (await session.execute(
            select(Level.id, Level.order_index).where(Level.module_id == gb_module.id)
        )).all():
            gb_by_order.setdefault(src_order, []).append(src_id)

    summary = {"levels": [], "generated": 0, "skipped_populated": 0,
               "skipped_has_drafts": 0, "skipped_no_source": 0, "errored": 0}
    for level_id, order_index in target_levels:
        entry = {"level_id": str(level_id), "status": "", "created": 0, "skipped": 0}
        src_ids = gb_by_order.get(order_index, [])
        if len(src_ids) != 1:
            entry["status"] = "skipped_no_source"
            summary["skipped_no_source"] += 1
            summary["levels"].append(entry)
            continue
        if not include_populated:
            lesson_n = await session.scalar(
                select(func.count(Lesson.id)).where(Lesson.level_id == level_id)
            )
            if lesson_n:
                entry["status"] = "skipped_populated"
                summary["skipped_populated"] += 1
                summary["levels"].append(entry)
                continue
            # Also skip a level that already has drafts waiting for review, so
            # re-running the batch doesn't stack duplicate drafts on it.
            draft_n = await session.scalar(
                select(func.count(LessonDraft.id)).where(LessonDraft.level_id == level_id)
            )
            if draft_n:
                entry["status"] = "skipped_has_drafts"
                summary["skipped_has_drafts"] += 1
                summary["levels"].append(entry)
                continue
        try:
            target_level = await session.get(Level, level_id)
            source_level = await session.get(Level, src_ids[0])
            result = await generate_market_level_lessons(
                session, target_level, source_level=source_level, brief=brief,
            )
            entry.update(status="generated", created=len(result.created), skipped=result.skipped)
            summary["generated"] += 1
        except Exception as exc:  # noqa: BLE001 — one level must not abort the module
            # Discard the failed level's flushed-but-uncommitted drafts so they
            # can't ride the NEXT level's commit into the DB. Safe to roll back:
            # the next iteration re-fetches its levels via session.get.
            await session.rollback()
            logger.warning("module batch gen failed for level %s: %s", level_id, exc)
            entry["status"] = "error"
            summary["errored"] += 1
        summary["levels"].append(entry)
    return summary
