from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_session
from .schemas import ChatThreadCreate, ChatThreadResponse
from .service import ChatThreadService

router = APIRouter(prefix="/api/v1/chat-threads", tags=["Chat"])


async def get_chat_service(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ChatThreadService:
    # agent 里带着 checkpointer，删除会话时用它清掉该会话的记忆
    agent = request.app.state.agent
    return ChatThreadService(session, agent)


@router.post("", response_model=ChatThreadResponse)
async def create_chat_thread(
    user_id: Annotated[int, Header(alias="x-user-id")],
    request: ChatThreadCreate,
    service: ChatThreadService = Depends(get_chat_service),
):
    return await service.add_chat_thread(user_id, request.title)


@router.delete("/{thread_id}", status_code=204, summary="删除会话（同时清理AI记忆）")
async def delete_chat_thread(
    thread_id: UUID,
    user_id: Annotated[int, Header(alias="x-user-id")],
    service: ChatThreadService = Depends(get_chat_service),
):
    await service.delete(thread_id, user_id)
    return Response(status_code=204)
