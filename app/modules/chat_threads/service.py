from uuid import UUID

from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from .exceptions import ChatThreadNotFoundError
from .models import ChatThread
from .repository import ChatRepository
from .schemas import (
    ChatHistoryResponse,
    ChatMessageResponse,
)

logger = get_logger(__name__)

# LangChain 消息类型 -> 对外暴露的角色
# 不在表里的类型（system / tool）属于 Agent 内部细节，不对外返回
ROLE_BY_MESSAGE_TYPE = {
    "human": "user",
    "ai": "assistant",
}


def _extract_text(content) -> str:
    """提取消息正文。

    普通消息 content 是字符串；开启 thinking 时 content 是内容块列表，
    这里只拼接其中的文本块。
    """
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = [
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        ]
        return "".join(parts).strip()
    return ""


class ChatThreadService:
    def __init__(self, session: AsyncSession, agent: CompiledStateGraph):
        self.session = session
        self.agent = agent
        self.repository = ChatRepository(session)

    async def add_chat_thread(self, user_id: int, title: str):
        async with self.session.begin():
            chat_thread = ChatThread(user_id=user_id, title=title)
            await self.repository.add_chat_thread(chat_thread)

            return chat_thread

    async def delete(self, thread_id: UUID, user_id: int) -> None:
        """删除会话，并连带清掉 LangGraph checkpointer 里该会话的记忆。

        没有这一步的话，checkpoints / checkpoint_blobs / checkpoint_writes 会一直累积，
        而且会话删掉后用户还会"记得"之前说过的话。
        """
        # 1.校验会话是否存在且属于当前用户（防止越权删除别人的记忆）
        chat_thread = await self.repository.find_owned(thread_id, user_id)
        if chat_thread is None:
            raise ChatThreadNotFoundError

        # 2.删除会话记录
        async with self.session.begin():
            await self.repository.delete(chat_thread)

        # 3.清理记忆：失败不影响会话删除的结果（会话已删除，残留记忆由清理脚本兜底）
        try:
            await self.agent.checkpointer.adelete_thread(str(thread_id))
        except Exception as e:
            logger.warning(f"清理会话记忆失败 thread_id={thread_id}: {e}")

    async def list_messages(
        self,
        thread_id: UUID,
        user_id: int,
    ) -> list[ChatMessageResponse]:
        """从 checkpointer 里读取该会话的历史消息。

        记忆本体存在 LangGraph 的 checkpoint_blobs 里，所以必须用
        str(thread_id) 作为 thread_id 去读，跟写入时的形式保持一致。
        """
        # 1.先查库校验会话归属（aget_state 区分不了"会话不存在"和"没聊过"）
        chat_thread = await self.repository.find_owned(thread_id, user_id)
        if chat_thread is None:
            raise ChatThreadNotFoundError

        # 2.读取状态快照
        state = await self.agent.aget_state(
            {"configurable": {"thread_id": str(thread_id)}}
        )
        messages = (state.values or {}).get("messages", []) if state else []

        # 3.映射成对外的消息结构
        result: list[ChatMessageResponse] = []
        for message in messages:
            role = ROLE_BY_MESSAGE_TYPE.get(getattr(message, "type", ""))
            if role is None:
                continue
            content = _extract_text(message.content)
            if not content:
                continue
            result.append(ChatMessageResponse(role=role, content=content))
        return result
