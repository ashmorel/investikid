"""Drift guard: the committed demo JSON must match the seed exactly.

If this fails, regenerate with: python -m scripts.export_demo_content
"""

import json

from scripts.export_demo_content import OUT_PATH, build_demo_content


def test_demo_content_json_matches_seed():
    assert OUT_PATH.exists(), (
        "frontend/src/demo/demoContent.json missing — run "
        "python -m scripts.export_demo_content"
    )
    committed = json.loads(OUT_PATH.read_text())
    assert committed == build_demo_content(), (
        "demoContent.json has drifted from the seed — regenerate with "
        "python -m scripts.export_demo_content"
    )


def test_demo_content_shape():
    demo = build_demo_content()
    assert demo["module_title"] == "What is a Stock?"
    assert demo["lessons"], "demo must have lessons"
    assert demo["lessons"][0]["type"] == "card"
    assert {le["type"] for le in demo["lessons"]} <= {"card", "video", "quiz", "scenario"}
    assert demo["tease"]["extra_level_count"] >= 2
    assert demo["tease"]["other_module_count"] >= 11
