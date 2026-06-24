import re

import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.handles import ADJECTIVES, ANIMALS, ensure_handle, generate_handle
from tests.test_content import _register_and_login

pytestmark = pytest.mark.asyncio(loop_scope="session")
HANDLE_RE = re.compile(r"^[A-Z][a-z]+[A-Z][a-z]+\d{2}$")

def test_generate_handle_shape():
    for _ in range(50):
        h = generate_handle()
        assert HANDLE_RE.match(h), h
        assert any(h.startswith(a) for a in ADJECTIVES)
        assert any(an in h for an in ANIMALS)

async def test_ensure_handle_assigns_and_persists(client, db_session):
    await _register_and_login(client, email="h1@example.com", username="h1")
    user = await db_session.scalar(select(User).where(User.email == "h1@example.com"))
    assert user.display_handle is None
    handle = await ensure_handle(db_session, user)
    await db_session.commit()
    assert HANDLE_RE.match(handle)
    await db_session.refresh(user)
    assert user.display_handle == handle
    # idempotent: returns the same handle, does not regenerate
    assert await ensure_handle(db_session, user) == handle
