from collections.abc import AsyncIterator

from fastapi.sse import ServerSentEvent
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.chat.schemas import ChatRequest
from app.modules.chat_threads.exceptions import ChatThreadNotFoundError
from app.modules.chat_threads.repository import ChatRepository


class ChatService:
    def __init__(self, session: AsyncSession, agent: CompiledStateGraph):
        self.repository = ChatRepository(session)
        self.agent = agent

    async def chat_stream(
        self,
        user_id: int,
        request: ChatRequest,
    ) -> AsyncIterator[ServerSentEvent]:
        # 1.校验会话是否属于当前用户
        thread = await self.repository.find_owned(
            request.thread_id,
            user_id,
        )
        if thread is None:
            raise ChatThreadNotFoundError

        # 2.校验通过后，调用Agent

        # 2.1.准备Agent输入
        _input = {"messages": [HumanMessage(content=request.message)]}
        config = {"configurable": {"thread_id": str(request.thread_id)}}

        # 2.2.使用v3协议获取异步事件流
        stream = await self.agent.astream_events(
            _input,
            config,
            version="v3",
        )

        # 2.3.只读取消息中的文本增量
        async for message in stream.messages:
            async for text in message.text:
                yield ServerSentEvent(data=text, event="message")
        # 2.4.返回结束标识
        yield ServerSentEvent(data="[DONE]", event="done")