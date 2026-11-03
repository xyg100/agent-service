"""ChatThreadService.delete 清理 LangGraph checkpoint 的单元测试。

不连数据库：session / repository / agent / checkpointer 全部用测试替身。
"""
from uuid import uuid4

import pytest

from app.modules.chat_threads.exceptions import ChatThreadNotFoundError
from app.modules.chat_threads.service import ChatThreadService


class FakeCheckpointer:
    """替代 AsyncPostgresSaver，只记录 adelete_thread 的调用。"""

    def __init__(self, error=None):
        self.deleted_thread_ids = []
        self._error = error

    async def adelete_thread(self, thread_id):
        if self._error is not None:
            raise self._error
        self.deleted_thread_ids.append(thread_id)


class FakeAgent:
    """替代 CompiledStateGraph，delete 只用到它的 checkpointer 属性。"""

    def __init__(self, checkpointer):
        self.checkpointer = checkpointer


class FakeRepository:
    """替代 ChatThreadRepository，只提供 find_owned 与 delete。"""

    def __init__(self, thread):
        self._thread = thread
        self.deleted = []

    async def find_owned(self, thread_id, user_id):
        return self._thread

    async def delete(self, chat_thread):
        self.deleted.append(chat_thread)


class _FakeTransaction:
    async def __aenter__(self):
        return None

    async def __aexit__(self, *exc_info):
        return False


class FakeSession:
    """替代 AsyncSession：begin() 只需返回一个异步上下文管理器。"""

    def begin(self):
        return _FakeTransaction()


def build_service(thread=object(), checkpointer_error=None):
    checkpointer = FakeCheckpointer(error=checkpointer_error)
    service = ChatThreadService(
        session=FakeSession(),
        agent=FakeAgent(checkpointer),
    )
    service.repository = FakeRepository(thread)
    return service, checkpointer


@pytest.mark.asyncio
async def test_delete_clears_checkpoint_using_str_thread_id():
    """删除会话时连带清掉 checkpointer 里的记忆，thread_id 形态与写入一致。"""
    thread = object()
    service, checkpointer = build_service(thread=thread)
    thread_id = uuid4()

    await service.delete(thread_id, user_id=1)

    assert service.repository.deleted == [thread]
    assert checkpointer.deleted_thread_ids == [str(thread_id)]


@pytest.mark.asyncio
async def test_delete_leaves_checkpoint_untouched_when_thread_not_owned():
    """会话不存在或不属于当前用户时，不能误删别人的记忆。"""
    service, checkpointer = build_service(thread=None)

    with pytest.raises(ChatThreadNotFoundError):
        await service.delete(uuid4(), user_id=999)

    assert service.repository.deleted == []
    assert checkpointer.deleted_thread_ids == []


@pytest.mark.asyncio
async def test_delete_still_succeeds_when_checkpoint_cleanup_fails():
    """清理记忆失败不应让整个删除请求失败——会话行已经删掉了。"""
    service, checkpointer = build_service(
        checkpointer_error=RuntimeError("checkpoint pool closed"),
    )

    await service.delete(uuid4(), user_id=1)

    assert len(service.repository.deleted) == 1
    assert checkpointer.deleted_thread_ids == []
