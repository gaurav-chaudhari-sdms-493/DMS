import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import engine
from app.models.tenant import Tenant
from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.services.chat_service import (
    create_chat_session,
    list_chat_sessions,
    get_chat_session,
    send_chat_message,
    delete_chat_session,
    _extract_score_threshold
)
from app.database import AsyncSessionLocal

def test_extract_score_threshold():
    assert _extract_score_threshold("filter documents which have score >= 85") == 0.85
    assert _extract_score_threshold("score > 90%") == 0.90
    assert _extract_score_threshold("score >= 0.8") == 0.8
    assert _extract_score_threshold("search for 12 marksheets") is None

@pytest.mark.asyncio
async def test_chat_session_crud():
    async with AsyncSessionLocal() as db_session:
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        tenant = Tenant(id=tenant_id, name=f"Test Chat Tenant {uuid.uuid4().hex[:6]}")
        user = User(id=user_id, tenant_id=tenant_id, email=f"chat_{uuid.uuid4().hex[:6]}@test.com", full_name="Chat Test", hashed_password="pw", role="user")
        db_session.add(tenant)
        db_session.add(user)
        await db_session.commit()

        # Create session
        session = await create_chat_session(tenant_id, user_id, "Test 12th Marksheets Chat", db_session)
        assert session.id is not None
        assert session.title == "Test 12th Marksheets Chat"

        # Send message
        reply = await send_chat_message(
            session_id=session.id,
            tenant_id=tenant_id,
            user_id=user_id,
            query="all diploma marksheets",
            db=db_session
        )
        assert reply is not None
        assert reply.role == "assistant"
        assert reply.content is not None

        # List sessions
        sessions = await list_chat_sessions(tenant_id, user_id, db_session)
        assert len(sessions) == 1
        assert sessions[0]["title"] == "Test 12th Marksheets Chat"

        # Get session
        fetched = await get_chat_session(session.id, tenant_id, user_id, db_session)
        assert fetched is not None
        assert fetched.id == session.id

        # Delete session
        deleted = await delete_chat_session(session.id, tenant_id, user_id, db_session)
        assert deleted is True
