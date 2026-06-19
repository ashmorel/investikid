from app.services.content_adaptation_check import find_uk_residue


def test_detects_uk_terms():
    found = find_uk_residue("Put £500 into your ISA — the FCA regulates it.")
    assert "£" in found and "ISA" in found and "FCA" in found


def test_clean_us_text_has_no_residue():
    assert find_uk_residue("Put $500 into your Roth IRA — the SEC regulates it.") == []


def test_word_boundary_not_substring():
    # 'crisp' contains 'isp' not 'ISA'; 'nice' must not match ' NI '
    assert find_uk_residue("That was a nice crisp explanation.") == []
