from app.services.email import _email_subject, _render, _render_html

FULL_CTX = {
    "parent_email": "parent@example.com",
    "week_start": "2026-06-01T00:00:00+00:00",
    "week_end": "2026-06-08T00:00:00+00:00",
    "parent_subscribed": False,
    "children": [
        {
            "name": "Maya",
            "masteries": [
                {
                    "module_title": "Saving Basics",
                    "level_title": "Level 2",
                    "objectives": [
                        "explain why saving matters",
                        "set a simple savings goal",
                    ],
                }
            ],
            "lessons_completed": 4,
            "streak": 3,
            "weak_topic": "Compound interest",
            "next_recommendation": {
                "module_title": "Shares 101",
                "level_title": "Level 1",
                "reason": "keep the momentum going",
            },
            "conversation_prompt": "Ask Maya what she would save for first.",
        },
        {
            "name": "Tom",
            "masteries": [],
            "lessons_completed": 2,
            "streak": 1,
            "weak_topic": None,
            "next_recommendation": None,
            "conversation_prompt": None,
        },
    ],
}

MINIMAL_CTX = {
    "parent_email": "parent@example.com",
    "week_start": "2026-06-01T00:00:00+00:00",
    "week_end": "2026-06-08T00:00:00+00:00",
    "parent_subscribed": True,
    "children": [
        {
            "name": "Maya",
            "masteries": [],
            "lessons_completed": 1,
            "streak": 0,
            "weak_topic": None,
            "next_recommendation": None,
            "conversation_prompt": None,
        }
    ],
}


def test_weekly_digest_subject_is_static_generic():
    assert _email_subject("weekly_digest") == "What your child learned this week 🌟"


def test_weekly_digest_text_full_context():
    body = _render("weekly_digest", FULL_CTX)
    assert "Maya" in body and "Tom" in body
    assert "Maya mastered Saving Basics · Level 2" in body
    assert "they can now explain why saving matters" in body
    assert "set a simple savings goal" in body
    assert "This week: 4 lessons · 3-day streak" in body
    assert "This week: 2 lessons · 1-day streak" in body
    assert "Worth practising: Compound interest" in body
    assert "Up next: Shares 101 — Level 1" in body
    assert "Talk about it: Ask Maya what she would save for first." in body
    # Premium nudge present for non-subscribed parents
    assert "Premium unlocks the next levels" in body
    assert "$" not in body and "£" not in body


def test_weekly_digest_text_minimal_context():
    body = _render("weekly_digest", MINIMAL_CTX)
    assert "Maya" in body
    assert "This week: 1 lessons · 0-day streak" in body
    assert "Worth practising" not in body
    assert "Up next" not in body
    assert "Talk about it" not in body
    # Subscribed parent: no premium paragraph
    assert "Premium unlocks" not in body
    # Footer always present
    assert "Manage email preferences in your dashboard settings." in body


def test_weekly_digest_html_full_context():
    html = _render_html("weekly_digest", FULL_CTX)
    assert "<!DOCTYPE html>" in html
    assert "Maya" in html and "Tom" in html
    assert "Saving Basics" in html
    assert "explain why saving matters" in html
    assert "Worth practising" in html and "Compound interest" in html
    assert "Up next" in html and "Shares 101" in html
    assert "Talk about it" in html
    assert "Premium unlocks the next levels" in html
    assert "/parent" in html
    assert "Manage email preferences in your dashboard settings." in html


def test_weekly_digest_html_minimal_context():
    html = _render_html("weekly_digest", MINIMAL_CTX)
    assert "<!DOCTYPE html>" in html
    assert "Maya" in html
    assert "Worth practising" not in html
    assert "Up next" not in html
    assert "Talk about it" not in html
    assert "Premium unlocks" not in html
    assert "/parent" in html
