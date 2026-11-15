from typing import Literal
from langchain_core.messages import AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from app.agents.schemas import (InsuranceAgentState,RouteResult,Intent)


# 一、定义节点

# 1.路由节点
async def route_node(
        state: InsuranceAgentState,
) -> Command[Intent]:
    """意图识别节点，后续再完善"""


    # 1.获取active_workflow，也就是上一轮会话的工作流
    previous_workflow = state.get("active_workflow", "")
    # 2.记录上轮工作流、本轮工作流
     #通过llm来意图识别接下来要goto的节点,所以intent的值由llm决定,这里先写死为chitchat用于演示
    intent = "chitchat"
    return Command(
        update={
            "previous_workflow": previous_workflow,
            "active_workflow": intent
        },
        goto=intent,
    )


# 2.闲聊节点
async def chitchat_node(state: InsuranceAgentState) -> dict:
    return {"messages": [AIMessage("你好，今天想聊点什么？")]}


# 3.保险推荐节点
async def recommendation_node(state: InsuranceAgentState) -> dict:
    return {"messages": [AIMessage("保险推荐工作流暂未接入。")]}


# 4.理赔节点
async def claim_node(state: InsuranceAgentState) -> dict:
    return {"messages": [AIMessage("理赔工作流暂未接入。")]}


# 5.人工节点
def human_handoff_node(state: InsuranceAgentState) -> dict:
    return {"messages": [AIMessage("已记录转人工请求，后续可接入人工客服系统。")]}


# 6.fallback节点
def fallback_node(state: InsuranceAgentState) -> dict:
    return {"messages": [AIMessage("我还不能确定你的需求，请说明是想咨询保险、推荐方案还是办理理赔。")]}

# 二、定义主Graph
def init_insurance_orchestrator(checkpointer: AsyncPostgresSaver):
    """初始化保险顾问主Graph"""

    builder = StateGraph(InsuranceAgentState)
    builder.add_node("route", route_node)
    builder.add_node("chitchat", chitchat_node)
    builder.add_node("recommendation_plan", recommendation_node)
    builder.add_node("claim", claim_node)
    builder.add_node("human_handoff", human_handoff_node)
    builder.add_node("fallback", fallback_node)

    builder.add_edge(START, "route")
    builder.add_edge("chitchat", END)
    builder.add_edge("recommendation_plan", END)
    builder.add_edge("claim", END)
    builder.add_edge("human_handoff", END)
    builder.add_edge("fallback", END)

    return builder.compile(checkpointer=checkpointer)









