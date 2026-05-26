"""Coach Eddie standalone service — context building and action parsing."""
from __future__ import annotations

import re
from typing import Any


_ACTION_RE = re.compile(
    r"\[ACTION:(lesson|module|review):([a-zA-Z0-9][a-zA-Z0-9\-]*)(?::([a-zA-Z0-9][a-zA-Z0-9\-]*))?\]"
)

_TYPE_LABELS = {
    "lesson": "Start lesson in {title}",
    "module": "Go to {title}",
    "review": "Review {title}",
}


def build_coach_context(
    *,
    strengths: list[dict[str, Any]],
    overall_mastery: float,
    continue_learning: list[dict[str, Any]],
    practise_again: list[dict[str, Any]],
    something_new: list[dict[str, Any]],
    due_count: int,
) -> str:
    """Build a human-readable learning-state block for the system prompt.

    All inputs are plain dicts — caller is responsible for shaping data
    from the various services into this format.
    """
    lines: list[str] = []

    if not strengths and not continue_learning and not practise_again and not something_new and due_count == 0:
        return "No learning data yet — this student is just getting started."

    lines.append("Your student's learning state:")

    # Topic mastery
    for t in strengths:
        score_pct = f"{round(t['mastery_score'] * 100)}%"
        weak = f", {t['weak_count']} weak concepts" if t.get("weak_count", 0) > 0 else ""
        topic_display = t["topic"].replace("_", " ")
        lines.append(f"- {topic_display}: {score_pct} mastery ({t['status']}){weak}")

    if overall_mastery > 0:
        lines.append(f"- Overall mastery: {round(overall_mastery * 100)}%")

    # Recommendations
    for item in continue_learning:
        pct = item.get("completed_pct", 0)
        lines.append(f"- Currently working on: {item['module_title']} ({pct}% complete)")

    for item in practise_again:
        concepts = item.get("weak_concepts", [])
        concept_str = f" — weak: {', '.join(concepts)}" if concepts else ""
        lines.append(f"- Needs practice: {item['module_title']}{concept_str}")

    for item in something_new:
        lines.append(f"- Suggested next: {item['module_title']} (something new)")

    # SR summary
    if due_count > 0:
        lines.append(f"- Due for review: {due_count} concept{'s' if due_count != 1 else ''}")

    return "\n".join(lines)


def parse_actions(
    raw_text: str,
    module_titles: dict[str, str],
) -> tuple[str, list[dict[str, Any]]]:
    """Extract [ACTION:...] markers from LLM text.

    Returns (cleaned_text, actions_list).
    """
    actions: list[dict[str, Any]] = []

    for match in _ACTION_RE.finditer(raw_text):
        action_type = match.group(1)
        module_id = match.group(2)
        lesson_id = match.group(3)  # may be None

        title = module_titles.get(module_id, "module")
        label = _TYPE_LABELS.get(action_type, "Go to {title}").format(title=title)

        # Use fallback label when module not found
        if module_id not in module_titles:
            label = _TYPE_LABELS.get(action_type, "Go to module").format(title="module")
            # Special case: "Go to module" is the expected fallback for unknown module ids
            if action_type == "module":
                label = "Go to module"

        actions.append({
            "type": action_type,
            "module_id": module_id,
            "lesson_id": lesson_id,
            "label": label,
        })

    cleaned = _ACTION_RE.sub("", raw_text).strip()

    return cleaned, actions
