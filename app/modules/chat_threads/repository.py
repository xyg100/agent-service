from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ChatThread


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_chat_thread(self, chat_thread: ChatThread):
        self.session.add(chat_thread)

    async def find_owned(
        self,
        thread_id: UUID,
        user_id: int,
    ) -> ChatThread | None:
        """按会话ID + 用户ID 查询会话（同时校验归属，防止越权访问）"""
        result = await self.session.scalar(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == user_id,
            )
        )
        return result

    async def delete(self, chat_thread: ChatThread) -> None:
        """删除会话记录"""
        await self.session.delete(chat_thread)
