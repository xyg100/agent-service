from typing import Annotated

from .schemas import *
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.infra.database import get_session
from app.modules.chat_threads.schemas import ChatHistoryResponse

