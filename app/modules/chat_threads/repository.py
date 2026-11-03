from sqlalchemy.ext.asyncio import AsyncSession
from .models import ChatThread
from sqlalchemy import select
from uuid import UUID


class ChatThreadRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, chat_thread: ChatThread):
        self.session.add(chat_thread)

    # 按用户查询会话列表
    async def list_by_user(self, user_id: int) -> list[ChatThread]:
        result = await self.session.scalars(
            select(ChatThread)
            .where(ChatThread.user_id == user_id)
            .order_by(
                ChatThread.updated_at.desc(),
                ChatThread.created_at.desc(),
            )
        )
        return list(result.all())

    # 按用户和会话ID查询会话
    async def find_owned(
            self,
            thread_id: UUID,
            user_id: int,
    ) -> ChatThread | None:
        result = await self.session.scalar(
            select(ChatThread).where(
                ChatThread.id == thread_id,
                ChatThread.user_id == user_id,
            )
        )
        return result

    # 删除会话
    async def delete(self, chat_thread: ChatThread):
        await self.session.delete(chat_thread)
