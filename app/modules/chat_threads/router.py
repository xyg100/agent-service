from typing import Annotated

from langchain_classic.schema import retriever

from .schemas import *
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.database import get_session
from app.modules.chat_threads.schemas import ChatHistoryResponse
from .service import ChatService

router = APIRouter(prefix="/api/v1/chat-threads", tags=["Chat"])


def get_chat_service(
        session: AsyncSession = Depends(get_session)
    ) -> ChatService:
    return ChatService(session)


@router.post("",response_model=ChatThreadResponse)
async def create_chat_thread(
        user_id: Annotated[int, Header(alias="x-user-id")],
        request = ChatThreadCreate,
        service = Depends(get_chat_service)
    ):
    return await service.add_chat_thread(user_id,request.title)



