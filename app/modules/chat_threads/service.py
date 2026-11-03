from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from .repository import ChatThreadRepository
from .models import ChatThread
from .exceptions import ChatThreadNotFoundError
from .schemas import ChatMessageResponse
from uuid import UUID
from uuid import UUID

from langchain_core.messages import AIMessage, HumanMessage

from app.modules.chat_threads.schemas import (
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


def extract_message_text(content) -> str:
    """从消息 content 中提取纯文本。

    content 通常是 str；开启 thinking 时会是内容块列表，
    此时只取其中 type == "text" 的块并拼接。
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            block.get("text", "")
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return ""


class ChatThreadService:

    def __init__(self, session: AsyncSession, agent: CompiledStateGraph):
        self.session = session
        self.repository = ChatThreadRepository(session)
        self.agent = agent

    async def list_messages(
            self,
            thread_id: UUID,
            user_id: int,
    ) -> list[ChatMessageResponse]:
        """读取指定会话的历史消息"""

        # 1.校验会话归属：aget_state 区分不了“会话不存在”与“没聊过”，
        #   两者都返回空 values，所以必须先查库
        thread = await self.repository.find_owned(thread_id, user_id)
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.从 checkpointer 读状态，thread_id 必须与写入时一致（str）
        state = await self.agent.aget_state(
            {"configurable": {"thread_id": str(thread_id)}}
        )
        raw_messages = (state.values or {}).get("messages") or []

        # 3.映射为对外结构，跳过内部消息与空内容（工具调用轮次常见）
        result = []
        for message in raw_messages:
            role = ROLE_BY_MESSAGE_TYPE.get(message.type)
            if role is None:
                continue
            text = extract_message_text(message.content)
            if not text.strip():
                continue
            result.append(ChatMessageResponse(role=role, content=text))
        return result

    async def add(self, user_id: int , title: str):
        # 用上下文管理，开启事务，运行完成，自动commit，出现异常，自动rollback
        async with self.session.begin():
            # 创建对象，对象 映射 到数据库 一条数据
            chat_thread = ChatThread(user_id = user_id, title = title)
            # 新增对象，就是插入一条数据
            await self.repository.add(chat_thread)

            return chat_thread

    async def list_by_user(self, user_id: int) -> list[ChatThread]:
        return await self.repository.list_by_user(user_id)

    """
    根据会话ID和用户ID重命名会话
    :param thread_id: 会话ID
    :param user_id: 用户ID
    :param title: 新的会话标题
    :return: 更新后的会话对象
    """
    async def rename(
            self,
            thread_id: UUID,
            user_id: int,
            title: str
    ) -> ChatThread:
        async with self.session.begin():
            # 1.根据thread_id和user_id查询，判断是否匹配
            thread = await self.repository.find_owned(thread_id, user_id)
            if thread is None:
                # 为None，说明不存在，或者不属于当前用户，抛出异常
                # raise: 就是指扔出去一个异常，代码会立刻终止，结束运行，把异常扔给调用者
                raise ChatThreadNotFoundError

            # 2.查询后直接修改字段，触发数据库更新
            thread.title = title

            # 3.刷新数据，重新从数据库中查出最新值
            await self.session.flush()
            await self.session.refresh(thread)

        return thread

    async def delete(
            self,
            thread_id: UUID,
            user_id: int,
    ) -> None:
        async with self.session.begin():
            thread = await self.repository.find_owned(thread_id, user_id)
            if thread is None:
                raise ChatThreadNotFoundError

            await self.repository.delete(thread)

        # 事务提交之后再清理 checkpointer 里的对话记忆。
        # 顺序不能反：先清记忆再删库，一旦删库失败就会出现
        # “会话还在列表里但历史空了”。
        try:
            await self.agent.checkpointer.adelete_thread(str(thread_id))
        except Exception:
            # 会话行已删除，对用户而言删除已经生效，
            # 清理失败只记录，不让整个请求失败
            logger.exception(f"清理会话记忆失败 thread_id={thread_id}")


    #获取历史对话消息
    async def get_history(
            self,
            thread_id: UUID,
            user_id: int,
    ) -> ChatHistoryResponse:
        # 1.校验会话归属
        thread = await self.repository.find_owned(thread_id, user_id)
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.读取Agent最新状态
        config = {"configurable": {"thread_id": str(thread_id)}}
        snapshot = await self.agent.aget_state(config)

        # 3.只保留用户消息和AI消息
        messages = []
        for message in snapshot.values.get("messages", []):
            if isinstance(message, HumanMessage):
                role = "user"
            elif isinstance(message, AIMessage):
                role = "assistant"
            else:
                continue

            if message.text:
                messages.append(
                    ChatMessageResponse(
                        role=role,
                        content=message.text,
                    )
                )

        return ChatHistoryResponse(
            thread_id=thread_id,
            messages=messages,
        )