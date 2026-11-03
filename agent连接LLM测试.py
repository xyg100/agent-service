# main.py
from dotenv import load_dotenv
import os
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

# 1.加载环境
load_dotenv()
api_key = os.getenv("DEEPSEEK_API_KEY")
print("api_key读取成功:", api_key is not None)

# 2.对接模型
model = init_chat_model(
    model="deepseek-v4-flash",
    model_provider="openai",
    api_key=api_key,
    base_url="https://api.deepseek.com"
)
print("模型对象创建完成")

# 3.定义工具
@tool
def get_weather(location: str) -> str:
    """查询指定城市的天气
    Args:
        location: 城市中文名称，例如杭州
    """
    return f"{location}，今日天气晴朗，25℃"

@tool
def square_root(x: float) -> str:
    """计算数字的平方根
    Args:
        x: 需要计算平方根的正数
    """
    return str(x ** 0.5)

tools = [get_weather, square_root]
print("工具定义完成")

# 4.创建agent
agent = create_agent(model, tools)
print("agent创建完成")

# 5.执行agent
resp = agent.invoke({
    "messages": [
        HumanMessage("杭州天气怎么样？")
    ]
})

print("\n=====最终回答=====")
print("\n第一次调用invoke")
print(resp["messages"][-1].content)
print("\n第二次调用invoke")
resp2 = agent.invoke({
    "messages": resp["messages"] + [HumanMessage("上海的天气呢,另外计算9的平方根")]
})
print(resp2["messages"][-1].content)


# 6.打印全部消息对象
print("\n=====完整消息列表=====")
for idx, msg in enumerate(resp2["messages"]):
    print(f"\n【{idx}】类型: {type(msg).__name__}")
    print(f"content: {msg.content}")
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        print(f"tool_calls: {msg.tool_calls}")
    if hasattr(msg, "tool_call_id"):
        print(f"tool_call_id: {msg.tool_call_id}")
