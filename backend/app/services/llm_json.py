from __future__ import annotations


def extract_json_list(parsed: object) -> list:
    """Return the list from a parsed LLM JSON response.

    LLM calls made with ``response_format="json"`` are forced into JSON *object*
    mode by some providers (notably OpenAI), so a model asked for an array will
    wrap it in an object under an arbitrary key (``modules`` / ``tips`` /
    ``items`` / ``suggestions`` / …). Other providers return the array directly.
    This normalizes both: a top-level list is returned as-is; for an object the
    first list-valued field is returned; anything else yields ``[]``.
    """
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        return next((v for v in parsed.values() if isinstance(v, list)), [])
    return []
