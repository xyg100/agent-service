from colorama import initialise
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.logging import get_logger
from .models import ChatThread
from .exceptions import ChatThreadNotFoundError
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from app.modules.chat_threads.schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
)
from .repository import ChatRepository

logger = get_logger(__name__)
# LangChain 消息类型 -> 对外暴露的角色
# 不在表里的类型（system / tool）属于 Agent 内部细节，不对外返回
ROLE_BY_MESSAGE_TYPE = {
    "human": "user",
    "ai": "assistant",
}

class ChatService():
    def __int__(self,session:AsyncSession):
        self.session = session
        self.repository = ChatRepository(session)

    async def add_chat_thread(self,user_id:int,title:str):
        async with self.session.begin():
            chat_thread = ChatThread(user_id = user_id,title = title)
            await self.repository.add_chat_thread(chat_thread)

            return chat_thread