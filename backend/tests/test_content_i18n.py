from app.services.content_i18n import apply_bundle, extract_bundle, source_hash


class FakeModule:
    title = "What is a Stock?"
    conversation_prompt = "Ask them what they own."


class FakeLesson:
    type = "quiz"
    content_json = {
        "question": "Q?", "choices": ["a", "b"], "answer_index": 1, "explanation": "because",
    }


def test_extract_module():
    b = extract_bundle("module", FakeModule())
    assert b == {"title": "What is a Stock?", "conversation_prompt": "Ask them what they own."}


def test_extract_lesson_quiz_excludes_answer_index():
    b = extract_bundle("lesson", FakeLesson())
    assert b == {"question": "Q?", "choices": ["a", "b"], "explanation": "because"}
    assert "answer_index" not in b


def test_source_hash_stable_and_sensitive():
    h1 = source_hash({"a": "x", "b": ["y"]})
    h2 = source_hash({"b": ["y"], "a": "x"})  # key order irrelevant
    assert h1 == h2
    assert source_hash({"a": "x"}) != source_hash({"a": "z"})


def test_apply_overlays_translation_keeping_excluded_fields():
    fields = {"question": "Q?", "choices": ["a", "b"], "answer_index": 1, "explanation": "because"}
    bundle = {"question": "Q-fr", "choices": ["a-fr", "b-fr"], "explanation": "parce que"}
    out = apply_bundle("lesson", fields, bundle)
    assert out["question"] == "Q-fr"
    assert out["choices"] == ["a-fr", "b-fr"]
    assert out["answer_index"] == 1  # untouched
