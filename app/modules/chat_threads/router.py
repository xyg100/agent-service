from typing import Annotated

from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_session
from .schemas import ChatThreadCreate, ChatThreadResponse
from .service import ChatThreadService

router = APIRouter(prefix="/api/v1/chat-threads", tags=["Chat"])


async def get_chat_service(
        session: AsyncSession = Depends(get_session)
) -> ChatThreadService:
    return ChatThreadService(session)


@router.post("", response_model=ChatThreadResponse)
async def create_chat_thread(
        user_id: Annotated[int, Header(alias="x-user-id")],
        request: ChatThreadCreate,
        service: ChatThreadService = Depends(get_chat_service)
):
    return await service.add_chat_thread(user_id, request.title)
