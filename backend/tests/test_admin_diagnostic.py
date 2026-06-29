"""Tests for the admin diagnostic-item review API (Task 3).

TDD: tests written first, run to fail, then the implementation lands.

Coverage:
- unauth (plain client) → 401/403 on every endpoint
- generate: mocked LLM returns drafts with correct market/topic/difficulty
- list: filter by market/topic/status; coverage summary reflects approved counts vs ≥2
- approve: sets status=approved + approved_by + approved_at; non-draft → 409
- edit: approved item → 409; draft item → works
- reject (draft→retired) and retire (approved→retired) transitions
- 404 on unknown id for by-id routes
"""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.models.diagnostic import DiagnosticItem
from app.services.moderation import ModerationResult

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_LLM_ITEM = {
    "question": "What is a stock?",
    "choices": ["A bond", "A share of a company", "A savings account", "A loan"],
    "answer_index": 1,
    "explanation": "A stock is a share of ownership in a company.",
    "concept_slug": None,
}

_LLM_RESPONSE = json.dumps({"items": [_LLM_ITEM, _LLM_ITEM]})

GENERATE_PAYLOAD = {
    "market_code": "US",
    "topic": "stocks",
    "difficulty_tier": 1,
    "count": 2,
}


def _item(db_session, **kwargs) -> DiagnosticItem:
    """Create a DiagnosticItem with sensible defaults for tests."""
    defaults = dict(
        market_code="US",
        topic="stocks",
        difficulty_tier=1,
        question="What is a share?",
        choices=["A", "B", "C", "D"],
        answer_index=0,
        explanation="A share is part of a company.",
        status="draft",
        source="generated",
        concept_id=None,
    )
    defaults.update(kwargs)
    row = DiagnosticItem(**defaults)
    db_session.add(row)
    return row


async def _seed_item(db_session, **kwargs) -> DiagnosticItem:
    row = _item(db_session, **kwargs)
    await db_session.flush()
    return row


# ---------------------------------------------------------------------------
# Unauth tests (plain `client`)
# ---------------------------------------------------------------------------


async def test_generate_requires_auth(client):
    resp = await client.post("/admin/diagnostic-items/generate", json=GENERATE_PAYLOAD)
    assert resp.status_code in (401, 403)


async def test_list_requires_auth(client):
    resp = await client.get("/admin/diagnostic-items")
    assert resp.status_code in (401, 403)


async def test_edit_requires_auth(client):
    resp = await client.patch(f"/admin/diagnostic-items/{uuid.uuid4()}", json={})
    assert resp.status_code in (401, 403)


async def test_approve_requires_auth(client):
    resp = await client.post(f"/admin/diagnostic-items/{uuid.uuid4()}/approve")
    assert resp.status_code in (401, 403)


async def test_reject_requires_auth(client):
    resp = await client.post(f"/admin/diagnostic-items/{uuid.uuid4()}/reject")
    assert resp.status_code in (401, 403)


async def test_retire_requires_auth(client):
    resp = await client.post(f"/admin/diagnostic-items/{uuid.uuid4()}/retire")
    assert resp.status_code in (401, 403)


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


async def test_generate_returns_drafts(admin_client, db_session):
    mock_client = AsyncMock()
    mock_client.complete = AsyncMock(return_value=_LLM_RESPONSE)
    with (
        patch(
            "app.services.diagnostic_item_service.get_llm_client",
            return_value=mock_client,
        ),
        patch(
            "app.services.diagnostic_item_service.moderate_output",
            AsyncMock(return_value=ModerationResult(safe=True, category=None, text="x")),
        ),
    ):
        resp = await admin_client.post(
            "/admin/diagnostic-items/generate", json=GENERATE_PAYLOAD
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    for item in data:
        assert item["market_code"] == "US"
        assert item["topic"] == "stocks"
        assert item["difficulty_tier"] == 1
        assert item["status"] == "draft"


# ---------------------------------------------------------------------------
# list + coverage summary
# ---------------------------------------------------------------------------


async def test_list_filters_by_market(admin_client, db_session):
    await _seed_item(db_session, market_code="GB", topic="savings", difficulty_tier=2)
    await _seed_item(db_session, market_code="US", topic="savings", difficulty_tier=2)

    resp = await admin_client.get("/admin/diagnostic-items?market_code=GB")
    assert resp.status_code == 200
    data = resp.json()
    items = data["items"]
    assert all(i["market_code"] == "GB" for i in items)


async def test_list_filters_by_topic(admin_client, db_session):
    await _seed_item(db_session, market_code="US", topic="budgeting", difficulty_tier=1)

    resp = await admin_client.get("/admin/diagnostic-items?market_code=US&topic=budgeting")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["topic"] == "budgeting" for i in items)


async def test_list_filters_by_status(admin_client, db_session):
    draft = await _seed_item(
        db_session, market_code="US", topic="risk", difficulty_tier=1, status="draft"
    )
    approved_row = await _seed_item(
        db_session, market_code="US", topic="risk", difficulty_tier=1, status="approved"
    )

    resp = await admin_client.get(
        "/admin/diagnostic-items?market_code=US&topic=risk&status=draft"
    )
    assert resp.status_code == 200
    ids = [i["id"] for i in resp.json()["items"]]
    assert str(draft.id) in ids
    assert str(approved_row.id) not in ids


async def test_coverage_summary_under_target(admin_client, db_session):
    """1 approved item in a cell → reported as under-covered (count=1 < 2)."""
    await _seed_item(
        db_session,
        market_code="US",
        topic="crypto",
        difficulty_tier=3,
        status="approved",
    )

    resp = await admin_client.get(
        "/admin/diagnostic-items?market_code=US&topic=crypto"
    )
    assert resp.status_code == 200
    coverage = resp.json()["coverage"]
    # Find the cell for (topic=crypto, difficulty_tier=3)
    cell = next(
        (c for c in coverage if c["topic"] == "crypto" and c["difficulty_tier"] == 3),
        None,
    )
    assert cell is not None
    assert cell["approved_count"] == 1  # under the ≥2 target


async def test_coverage_summary_met(admin_client, db_session):
    """2 approved items in a cell → at or above target."""
    for _ in range(2):
        await _seed_item(
            db_session,
            market_code="US",
            topic="debt",
            difficulty_tier=2,
            status="approved",
        )

    resp = await admin_client.get(
        "/admin/diagnostic-items?market_code=US&topic=debt"
    )
    assert resp.status_code == 200
    coverage = resp.json()["coverage"]
    cell = next(
        (c for c in coverage if c["topic"] == "debt" and c["difficulty_tier"] == 2),
        None,
    )
    assert cell is not None
    assert cell["approved_count"] >= 2


# ---------------------------------------------------------------------------
# approve
# ---------------------------------------------------------------------------


async def test_approve_sets_fields(admin_client, db_session):
    row = await _seed_item(db_session, status="draft")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/approve")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "approved"
    assert data["approved_by"] is not None
    assert data["approved_at"] is not None


async def test_approve_already_approved_is_409(admin_client, db_session):
    row = await _seed_item(db_session, status="approved")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/approve")
    assert resp.status_code == 409


async def test_approve_retired_is_409(admin_client, db_session):
    row = await _seed_item(db_session, status="retired")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/retire")
    # retire on an already-retired item should also fail (not approved)
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# edit
# ---------------------------------------------------------------------------


async def test_edit_draft_works(admin_client, db_session):
    row = await _seed_item(db_session, status="draft")
    resp = await admin_client.patch(
        f"/admin/diagnostic-items/{row.id}",
        json={"question": "Updated question?"},
    )
    assert resp.status_code == 200
    assert resp.json()["question"] == "Updated question?"


async def test_edit_approved_is_409(admin_client, db_session):
    row = await _seed_item(db_session, status="approved")
    resp = await admin_client.patch(
        f"/admin/diagnostic-items/{row.id}",
        json={"question": "Should not be allowed"},
    )
    assert resp.status_code == 409


async def test_edit_retired_is_409(admin_client, db_session):
    row = await _seed_item(db_session, status="retired")
    resp = await admin_client.patch(
        f"/admin/diagnostic-items/{row.id}",
        json={"question": "Also not allowed"},
    )
    assert resp.status_code == 409


async def test_edit_validates_choices_count(admin_client, db_session):
    row = await _seed_item(db_session, status="draft")
    resp = await admin_client.patch(
        f"/admin/diagnostic-items/{row.id}",
        json={"choices": ["A", "B", "C"]},  # only 3, need 4
    )
    assert resp.status_code == 422


async def test_edit_validates_answer_index_range(admin_client, db_session):
    row = await _seed_item(db_session, status="draft")
    resp = await admin_client.patch(
        f"/admin/diagnostic-items/{row.id}",
        json={"answer_index": 5},  # out of range for 4 choices
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# reject (draft → retired)
# ---------------------------------------------------------------------------


async def test_reject_transitions_to_retired(admin_client, db_session):
    row = await _seed_item(db_session, status="draft")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/reject")
    assert resp.status_code == 200
    assert resp.json()["status"] == "retired"


async def test_reject_non_draft_is_409(admin_client, db_session):
    row = await _seed_item(db_session, status="approved")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/reject")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# retire (approved → retired)
# ---------------------------------------------------------------------------


async def test_retire_transitions_to_retired(admin_client, db_session):
    row = await _seed_item(db_session, status="approved")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/retire")
    assert resp.status_code == 200
    assert resp.json()["status"] == "retired"


async def test_retire_draft_is_409(admin_client, db_session):
    row = await _seed_item(db_session, status="draft")
    resp = await admin_client.post(f"/admin/diagnostic-items/{row.id}/retire")
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# 404 on unknown id
# ---------------------------------------------------------------------------


async def test_approve_unknown_id_is_404(admin_client):
    resp = await admin_client.post(f"/admin/diagnostic-items/{uuid.uuid4()}/approve")
    assert resp.status_code == 404


async def test_reject_unknown_id_is_404(admin_client):
    resp = await admin_client.post(f"/admin/diagnostic-items/{uuid.uuid4()}/reject")
    assert resp.status_code == 404


async def test_retire_unknown_id_is_404(admin_client):
    resp = await admin_client.post(f"/admin/diagnostic-items/{uuid.uuid4()}/retire")
    assert resp.status_code == 404


async def test_edit_unknown_id_is_404(admin_client):
    resp = await admin_client.patch(
        f"/admin/diagnostic-items/{uuid.uuid4()}", json={"question": "x?"}
    )
    assert resp.status_code == 404
