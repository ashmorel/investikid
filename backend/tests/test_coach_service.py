from app.services.coach_service import build_coach_context, parse_actions


class TestBuildCoachContext:
    def test_empty_state(self):
        ctx = build_coach_context(
            strengths=[],
            overall_mastery=0.0,
            continue_learning=[],
            practise_again=[],
            something_new=[],
            due_count=0,
        )
        assert "No learning data yet" in ctx

    def test_with_strengths_and_gaps(self):
        ctx = build_coach_context(
            strengths=[
                {"topic": "stocks", "mastery_score": 0.85, "status": "strong", "weak_count": 0, "due_for_review": 0},
                {"topic": "budgeting", "mastery_score": 0.45, "status": "needs_practice", "weak_count": 2, "due_for_review": 1},
            ],
            overall_mastery=0.65,
            continue_learning=[],
            practise_again=[],
            something_new=[],
            due_count=1,
        )
        assert "stocks" in ctx
        assert "85%" in ctx
        assert "budgeting" in ctx
        assert "45%" in ctx
        assert "2 weak" in ctx
        assert "Due for review: 1" in ctx

    def test_with_recommendations(self):
        ctx = build_coach_context(
            strengths=[],
            overall_mastery=0.0,
            continue_learning=[{"module_title": "Stocks 101", "completed_pct": 60}],
            practise_again=[{"module_title": "Budgeting", "weak_concepts": ["APR", "compound interest"]}],
            something_new=[{"module_title": "Risk Basics"}],
            due_count=0,
        )
        assert "Stocks 101" in ctx
        assert "60%" in ctx
        assert "Budgeting" in ctx
        assert "APR" in ctx
        assert "Risk Basics" in ctx

    def test_due_count_zero_omitted(self):
        ctx = build_coach_context(
            strengths=[],
            overall_mastery=0.0,
            continue_learning=[],
            practise_again=[],
            something_new=[],
            due_count=0,
        )
        assert "Due for review" not in ctx


class TestParseActions:
    def test_no_markers(self):
        text, actions = parse_actions("You're doing great!", module_titles={})
        assert text == "You're doing great!"
        assert actions == []

    def test_single_lesson_action(self):
        raw = "Try this! [ACTION:lesson:mod-1:L2] It's fun."
        text, actions = parse_actions(raw, module_titles={"mod-1": "Stocks 101"})
        assert "[ACTION:" not in text
        assert text == "Try this!  It's fun."
        assert len(actions) == 1
        assert actions[0]["type"] == "lesson"
        assert actions[0]["module_id"] == "mod-1"
        assert actions[0]["lesson_id"] == "L2"
        assert "Stocks 101" in actions[0]["label"]

    def test_module_action_no_lesson(self):
        raw = "Check out [ACTION:module:mod-2]"
        text, actions = parse_actions(raw, module_titles={"mod-2": "Budgeting"})
        assert len(actions) == 1
        assert actions[0]["type"] == "module"
        assert actions[0]["lesson_id"] is None
        assert "Budgeting" in actions[0]["label"]

    def test_review_action(self):
        raw = "Time to review! [ACTION:review:mod-3]"
        text, actions = parse_actions(raw, module_titles={"mod-3": "Savings"})
        assert actions[0]["type"] == "review"
        assert "Savings" in actions[0]["label"]

    def test_multiple_actions(self):
        raw = "A [ACTION:lesson:m1:L1] and B [ACTION:module:m2]"
        text, actions = parse_actions(raw, module_titles={"m1": "M1", "m2": "M2"})
        assert len(actions) == 2

    def test_malformed_marker_ignored(self):
        raw = "Bad [ACTION:unknown] marker"
        text, actions = parse_actions(raw, module_titles={})
        assert actions == []
        # Malformed marker stays in text (not a valid pattern)
        assert "Bad" in text

    def test_unknown_module_id_uses_fallback_label(self):
        raw = "[ACTION:module:unknown-id]"
        text, actions = parse_actions(raw, module_titles={})
        assert len(actions) == 1
        assert actions[0]["label"] == "Go to module"
