from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import uuid

from app.schemas.chat import (
    ChatSessionSchema,
    ChatSessionListItem,
    ChatMessageSchema,
    CreateSessionRequest,
    SendMessageRequest,
    UpdateSessionRequest
)
from app.schemas.auth import TokenPayload
from app.deps import get_db, require_tenant_access, get_request_ip
from app.services import chat_service

router = APIRouter()

@router.post("/sessions", response_model=ChatSessionSchema, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: CreateSessionRequest,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)

    session = await chat_service.create_chat_session(
        tenant_id=tenant_id,
        user_id=user_id,
        title=body.title,
        db=db
    )
    return session

@router.get("/sessions", response_model=List[ChatSessionListItem])
async def list_sessions(
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)

    return await chat_service.list_chat_sessions(
        tenant_id=tenant_id,
        user_id=user_id,
        db=db
    )

@router.get("/sessions/{session_id}", response_model=ChatSessionSchema)
async def get_session(
    session_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)

    session = await chat_service.get_chat_session(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        db=db
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session

@router.patch("/sessions/{session_id}", response_model=ChatSessionSchema)
async def update_session_title(
    session_id: uuid.UUID,
    body: UpdateSessionRequest,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)

    session = await chat_service.update_chat_session_title(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        title=body.title,
        db=db
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session

@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)

    deleted = await chat_service.delete_chat_session(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        db=db
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return None

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageSchema)
async def send_message(
    session_id: uuid.UUID,
    body: SendMessageRequest,
    request: Request,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db)
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    ip_addr = await get_request_ip(request)

    try:
        msg = await chat_service.send_chat_message(
            session_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
            query=body.query,
            explicit_filters=body.filters,
            db=db,
            ip_address=ip_addr
        )
        return msg
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
