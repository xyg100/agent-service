import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

# 1.准备和加载环境变量
load_dotenv()

# 2.定义工具
from langchain_mcp_adapters.client import MultiServerMCPClient

# 连接Time MCP服务器
client = MultiServerMCPClient(
    {
        "math": {
            "transport": "stdio",
            "command": "python",
            "args": ["math_mcp_server.py"]
        }
    }
)

async def run():
    # 注意MultiServerMCPClient是异步的，结果都是协程对象，需要await
    tools = await client.get_tools()


    # 3.创建Agent，绑定model和tools
    agent = create_agent(
        model=init_chat_model(
            "deepseek-v4-flash",
            extra_body={"thinking": {"type": "disabled"}}
        ),
        tools=tools
    )

    # 4.调用agent
    response = await agent.ainvoke({
        "messages": [HumanMessage("429和327的平方根的和是多少")]
    })

    for m in response['messages']:
        m.pretty_print()

asyncio.run(run())