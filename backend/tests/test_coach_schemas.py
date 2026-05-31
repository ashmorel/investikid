import uuid

from app.schemas.ai import CoachAction, CoachChatRequest, CoachChatResponse


def test_coach_chat_request_defaults():
    req = CoachChatRequest(message="What should I learn?")
    assert req.message == "What should I learn?"
    assert req.conversation_id is None


def test_coach_chat_request_with_conversation_id():
    cid = uuid.uuid4()
    req = CoachChatRequest(message="hi", conversation_id=cid)
    assert req.conversation_id == cid


def test_coach_action_without_lesson():
    a = CoachAction(type="module", module_id="m1", label="Go to M1")
    assert a.lesson_id is None
    assert a.type == "module"


def test_coach_action_with_lesson():
    a = CoachAction(type="lesson", module_id="m1", lesson_id="L1", label="Start L1")
    assert a.lesson_id == "L1"


def test_coach_chat_response_shape():
    resp = CoachChatResponse(
        response="Try stocks!",
        conversation_id=uuid.uuid4(),
        messages_remaining=4,
        actions=[CoachAction(type="module", module_id="m1", label="Go")],
    )
    assert len(resp.actions) == 1
    assert resp.messages_remaining == 4


def test_coach_chat_response_empty_actions():
    resp = CoachChatResponse(
        response="You're doing great!",
        conversation_id=uuid.uuid4(),
        messages_remaining=3,
        actions=[],
    )
    assert resp.actions == []
