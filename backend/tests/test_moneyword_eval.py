from app.services.moneyword_service import evaluate_guess


def test_all_correct():
    assert evaluate_guess("ASSET", "ASSET") == ["correct"] * 5

def test_present_and_absent():
    # answer ASSET, guess STEAL: S present, T present, E present, A present, L absent
    assert evaluate_guess("ASSET", "STEAL") == ["present", "present", "present", "present", "absent"]

def test_duplicate_letters_consume_once():
    # answer ROBOT (two O), guess BOOKS: B present, O correct(pos2), O present? — only one O left after the correct
    res = evaluate_guess("ROBOT", "OOOOO")
    # ROBOT has 2 O's at positions 1 and 3 → those two are correct, the other three O's are absent
    assert res == ["absent", "correct", "absent", "correct", "absent"]
