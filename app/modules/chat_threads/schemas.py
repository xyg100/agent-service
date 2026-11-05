from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
"""
schemas : 入参和出参数据定义
自定义类继承BaseModel,定义字段和类型,用于对数据的校验和转换
格式:
    ① 字段 : 类型 = Field ( ... )    #Field 是 Pydantic 的字段描述器：给一个字段附加“默认值 、 校验规则 、 元数据”, 没有默认值就说明是必填项,前端必须来值
  或② 字段 : 类型
"""

class ChatThreadCreate(BaseModel):
    """创建会话请求"""

    title: str = Field(default="新会话", min_length=1, max_length=200)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip()



class ChatThreadRename(BaseModel):
    """重命名会话请求"""

    title: str = Field(min_length=1, max_length=200)

    @field_validator("title", mode="before")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return value.strip()

class ChatThreadResponse(BaseModel):
    """会话响应"""
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

class ChatMessageResponse(BaseModel):
    """历史消息响应"""

    role: Literal["user", "assistant"]
    content: str

class ChatHistoryResponse(BaseModel):
    """会话历史响应"""

    thread_id: UUID
    messages: list[ChatMessageResponse]