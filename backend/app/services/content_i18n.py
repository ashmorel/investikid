from __future__ import annotations

import hashlib
import json
from typing import Any

# Translatable lesson content_json keys per lesson type. Scalars + list[str]
# unless noted. Anything not listed (ids, indices, youtube_id, transcript) is
# NEVER translated and is preserved verbatim on serve.
_LESSON_FIELDS: dict[str, list[str]] = {
    "card": ["title", "body"],
    "quiz": ["question", "choices", "explanation"],
    "scenario": ["prompt"],   # scenario.choices handled specially (list of {label, outcome})
    "video": ["caption"],
}


def extract_bundle(entity_type: str, entity: Any) -> dict:
    """The English bundle of translatable strings for an entity. Omits None/empty."""
    if entity_type == "module":
        out: dict[str, Any] = {"title": entity.title}
        if getattr(entity, "conversation_prompt", None):
            out["conversation_prompt"] = entity.conversation_prompt
        return out
    if entity_type == "level":
        out = {"title": entity.title}
        objs = getattr(entity, "learning_objectives", None)
        if objs:
            out["learning_objectives"] = list(objs)
        return out
    if entity_type == "lesson":
        cj = entity.content_json or {}
        keys = _LESSON_FIELDS.get(entity.type, [])
        out = {k: cj[k] for k in keys if k in cj and cj[k] not in (None, "")}
        # scenario choices: list of {label, outcome}
        if entity.type == "scenario" and isinstance(cj.get("choices"), list):
            out["choices"] = [
                {"label": c.get("label", ""), "outcome": c.get("outcome", "")}
                for c in cj["choices"]
            ]
        return out
    raise ValueError(f"unknown entity_type {entity_type!r}")


def source_hash(bundle: dict) -> str:
    return hashlib.sha256(
        json.dumps(bundle, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def apply_bundle(entity_type: str, fields: dict, bundle: dict) -> dict:
    """Overlay a translation bundle onto an entity's served fields. For lesson,
    `fields` is the content_json; only translatable keys are overridden."""
    out = dict(fields)
    if entity_type in ("module", "level"):
        for k, v in bundle.items():
            out[k] = v
        return out
    # lesson: override content_json text keys; scenario choices merge by index
    for k, v in bundle.items():
        if k == "choices" and isinstance(v, list) and isinstance(out.get("choices"), list):
            merged = []
            for orig, tr in zip(out["choices"], v):
                if isinstance(orig, dict):  # scenario {label, outcome, ...}
                    m = dict(orig)
                    m["label"] = tr.get("label", orig.get("label"))
                    m["outcome"] = tr.get("outcome", orig.get("outcome"))
                    merged.append(m)
                else:  # quiz choices: plain strings
                    merged.append(tr)
            # keep any extra original choices if lengths differ (defensive)
            merged += out["choices"][len(v):]
            out["choices"] = merged
        else:
            out[k] = v
    return out


def validate_bundle(entity_type: str, source: dict, translated: dict) -> bool:
    """Structural validation: same keys; same option counts; non-empty strings."""
    if set(source.keys()) != set(translated.keys()):
        return False
    for k, sv in source.items():
        tv = translated.get(k)
        if isinstance(sv, str):
            if not isinstance(tv, str) or not tv.strip():
                return False
        elif isinstance(sv, list):
            if not isinstance(tv, list) or len(tv) != len(sv):
                return False
            for s_item, t_item in zip(sv, tv):
                if isinstance(s_item, dict):  # scenario choice
                    if not isinstance(t_item, dict):
                        return False
                    if not str(t_item.get("label", "")).strip() or not str(t_item.get("outcome", "")).strip():
                        return False
                elif not isinstance(t_item, str) or not t_item.strip():
                    return False
        else:
            return False
    return True
