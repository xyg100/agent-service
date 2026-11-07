from sqlalchemy.ext.asyncio import AsyncSession
from .models import ChatThread
from sqlalchemy import select
from uuid import UUID

class ChatRepository:
    def __init__(self,session:AsyncSession):
        self.session = session

    async def add_chat_thread(self,chat_thread:ChatThread):
        self.session.add(chat_thread)


