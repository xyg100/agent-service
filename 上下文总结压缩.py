from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.middleware import SummarizationMiddleware

# 1.准备和加载环境变量
load_dotenv()

# 2.初始化模型
model = init_chat_model(
        "deepseek-v4-flash",
        extra_body={"thinking": {"type": "disabled"}}
    )

# 3.准备tools
tools = []

# 4.初始化消息摘要中间件
middleware = SummarizationMiddleware(
    model=model,
    trigger=("messages", 6), #  触发时机，当消息数超过6时，进行总结
    keep=("messages", 1) #  保留的会话数
)

# 5.创建Agent，绑定model、tools、checkpointer、Middleware
agent = create_agent(
    model=model,
    tools=tools, # 可省略
    checkpointer=InMemorySaver(),
    middleware=[middleware]
)

config = {"configurable": {"thread_id": "t1"}}

# 6.调用Agent
# 制造长会话历史
agent.invoke({"messages": "你好，我是虎哥."}, config)
agent.invoke({"messages": "我最喜欢的运动是乒乓"}, config)
agent.invoke({"messages": "我最喜欢的动物是猫猫"}, config)

# 测试效果
final_response = agent.invoke({"messages": "你还记得我吗？"}, config)


for message in final_response["messages"]:
    message.pretty_print()