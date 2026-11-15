from dataclasses import dataclass
from typing import Literal

from langgraph.graph import MessagesState
from pydantic import BaseModel, Field

# 路由意图常量
Intent = Literal[
    "chitchat",
    "recommendation_plan",
    "claim",
    "human_handoff",
    "fallback",
]


class RouteResult(BaseModel):
    """意图识别结果"""

    intent: Intent = Field(description="本轮消息应该进入的工作流")
    reason: str = Field(description="判断该意图的理由")


class InsuranceAgentState(MessagesState):
    """保险顾问主Graph状态"""

    previous_workflow: Intent
    active_workflow: Intent