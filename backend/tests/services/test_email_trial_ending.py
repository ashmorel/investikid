from app.services.email import _email_subject, _render, _render_html

CTX = {
    "child_label": "Sophie",
    "trial_end": "Friday 12 June",
    "benefits": ["Coach Penny", "Premium lessons"],
    "manage_hint": "Open InvestiKid to manage your plan.",
}


def test_trial_ending_subject():
    assert _email_subject("trial_ending") == "Your InvestiKid trial ends soon"


def test_trial_ending_text_has_child_date_benefits_no_price():
    body = _render("trial_ending", CTX)
    assert "Sophie" in body
    assert "Friday 12 June" in body
    assert "Coach Penny" in body
    assert "Open InvestiKid to manage your plan." in body
    assert "$" not in body and "£" not in body


def test_trial_ending_html_renders_benefits_and_cta():
    html = _render_html("trial_ending", CTX)
    assert "<!DOCTYPE html>" in html
    assert "Your InvestiKid trial ends soon" in html
    assert "<li" in html and "Premium lessons" in html
    assert "/parent" in html
