"""聊天会话模块的异常类"""

from app.core.exceptions import ApplicationError


class ChatThreadError(ApplicationError):
    """聊天会话业务异常基类"""
    status_code: int = 400
    code: str = "CHAT_THREAD_ERROR"
    message: str = "聊天会话操作失败"


class ChatThreadNotFoundError(ChatThreadError):
    """会话不存在或不属于当前用户"""
    status_code = 404
    code = "CHAT_THREAD_NOT_FOUND"
    message = "会话不存在或不属于当前用户"


class ChatThreadPermissionError(ChatThreadError):
    """无权限访问会话"""
    status_code = 403
    code = "CHAT_THREAD_PERMISSION_DENIED"
    message = "无权限访问该会话"
