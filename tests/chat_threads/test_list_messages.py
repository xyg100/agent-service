"""ChatThreadService.list_messages 的单元测试。

不连数据库、不调用 LLM：agent 与 repository 都用测试替身注入。
"""
from types import SimpleNamespace
from uuid import uuid4

import pytest
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from app.modules.chat_threads.exceptions import ChatThreadNotFoundError
from app.modules.chat_threads.service import ChatThreadService


class FakeAgent:
    """替代 CompiledStateGraph，只提供 aget_state。

    实测真实行为：aget_state 永远返回 StateSnapshot（不会是 None），
    无 checkpoint 时 values 为空字典。
    """

    def __init__(self, values):
        self._values = values
        self.received_config = None

    async def aget_state(self, config):
        self.received_config = config
        return SimpleNamespace(values=self._values)


class FakeRepository:
    """替代 ChatThreadRepository，只提供 find_owned。"""

    def __init__(self, thread):
        self._thread = thread

    async def find_owned(self, thread_id, user_id):
        return self._thread


def build_service(messages, thread=object()):
    """构造一个不依赖真实 session 的 ChatThreadService。"""
    service = ChatThreadService(
        session=None,
        agent=FakeAgent({"messages": messages}),
    )
    service.repository = FakeRepository(thread)
    return service


@pytest.mark.asyncio
async def test_list_messages_maps_human_and_ai_in_order():
    """human/ai 消息按原顺序映射为 user/assistant。"""
    service = build_service([
        HumanMessage(content="重疾险保什么"),
        AIMessage(content="重疾险对约定重大疾病一次性给付保额。"),
    ])

    result = await service.list_messages(uuid4(), user_id=1)

    assert [(m.role, m.content) for m in result] == [
        ("user", "重疾险保什么"),
        ("assistant", "重疾险对约定重大疾病一次性给付保额。"),
    ]


@pytest.mark.asyncio
async def test_list_messages_skips_tool_and_system_messages():
    """system / tool 属于 Agent 内部细节，不对外返回。"""
    service = build_service([
        SystemMessage(content="你是“安心保”的智能保险顾问。"),
        HumanMessage(content="上海天气如何"),
        AIMessage(content="", tool_calls=[
            {"name": "get_weather", "args": {"location": "上海"}, "id": "call_1"},
        ]),
        ToolMessage(content="晴", tool_call_id="call_1"),
        AIMessage(content="上海今天晴。"),
    ])

    result = await service.list_messages(uuid4(), user_id=1)

    assert [(m.role, m.content) for m in result] == [
        ("user", "上海天气如何"),
        ("assistant", "上海今天晴。"),
    ]


@pytest.mark.asyncio
async def test_list_messages_skips_messages_with_blank_content():
    """工具调用轮次的 AI 消息 content 为空，不应返回空气泡。"""
    service = build_service([
        HumanMessage(content="   "),
        AIMessage(content=""),
        AIMessage(content="医疗险可以报销住院费用。"),
    ])

    result = await service.list_messages(uuid4(), user_id=1)

    assert [(m.role, m.content) for m in result] == [
        ("assistant", "医疗险可以报销住院费用。"),
    ]


@pytest.mark.asyncio
async def test_list_messages_joins_text_blocks_when_content_is_list():
    """开启 thinking 时 content 是内容块列表，应拼接其中的文本块。"""
    service = build_service([
        HumanMessage(content="重疾险和医疗险区别"),
        AIMessage(content=[
            {"type": "reasoning", "reasoning": "先对比给付方式"},
            {"type": "text", "text": "重疾险是给付型，"},
            {"type": "text", "text": "医疗险是报销型。"},
        ]),
    ])

    result = await service.list_messages(uuid4(), user_id=1)

    assert [(m.role, m.content) for m in result] == [
        ("user", "重疾险和医疗险区别"),
        ("assistant", "重疾险是给付型，医疗险是报销型。"),
    ]


@pytest.mark.asyncio
async def test_list_messages_returns_empty_list_when_no_checkpoint():
    """会话存在但从未聊过，aget_state 给空 values，应返回 []。"""
    service = ChatThreadService(session=None, agent=FakeAgent({}))
    service.repository = FakeRepository(object())

    result = await service.list_messages(uuid4(), user_id=1)

    assert result == []


@pytest.mark.asyncio
async def test_list_messages_passes_thread_id_as_str_to_agent():
    """写入时用的是 str(thread_id)，读取必须一致，否则永远读不到记忆。"""
    thread_id = uuid4()
    agent = FakeAgent({})
    service = ChatThreadService(session=None, agent=agent)
    service.repository = FakeRepository(object())

    await service.list_messages(thread_id, user_id=1)

    assert agent.received_config == {
        "configurable": {"thread_id": str(thread_id)},
    }


@pytest.mark.asyncio
async def test_list_messages_raises_not_found_when_thread_not_owned():
    """aget_state 区分不了“会话不存在”与“没聊过”，必须先查库校验归属。"""
    service = build_service([HumanMessage(content="不该被读到")], thread=None)

    with pytest.raises(ChatThreadNotFoundError):
        await service.list_messages(uuid4(), user_id=999)
