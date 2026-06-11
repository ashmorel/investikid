"""Export the demo module's Level 1 from the seed into the frontend bundle.

The public /try demo renders this JSON with zero API calls. Run after any
change to the demo module's Level 1 content:

    python -m scripts.export_demo_content

tests/test_demo_export.py fails CI whenever the committed JSON drifts from
the seed, so the demo can never silently go stale.
"""

import json
from pathlib import Path

from app.seed.content import _MODULES

DEMO_TOPIC = "stocks"
DEMO_TITLE = "What is a Stock?"
OUT_PATH = (
    Path(__file__).resolve().parents[2]
    / "frontend" / "src" / "demo" / "demoContent.json"
)


def build_demo_content() -> dict:
    spec = next(
        m for m in _MODULES if m["topic"] == DEMO_TOPIC and m["title"] == DEMO_TITLE
    )
    return {
        "module_title": spec["title"],
        "icon": spec.get("icon", "📚"),
        "learning_objectives": spec.get("learning_objectives") or [],
        "lessons": [
            {
                "type": le["type"],
                "xp_reward": le["xp_reward"],
                "content_json": le["content_json"],
            }
            for le in spec["lessons"]
        ],
        "tease": {
            "extra_level_count": len(spec.get("extra_levels", [])),
            "other_module_count": len(_MODULES) - 1,
        },
    }


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(build_demo_content(), ensure_ascii=False, indent=2) + "\n"
    )
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
