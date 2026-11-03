# -*- coding: utf-8 -*-
"""
最小可运行的 Agent 循环演示 —— 不需要 API Key。

用一个"假模型"顶替真实 LLM，把框架侧要做的每一步原样打印出来：
  1) 发给模型的请求长什么样（messages 数组就是全部信道）
  2) 模型返回的"特殊文本"长什么样
  3) 框架如何执行工具、如何把结果塞回去、如何决定继续还是结束

看完这个文件，你就知道 agent 框架为什么可以只写几百行。
"""
import datetime
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BAR = "=" * 72


# ─────────────────────────────────────────────────────────────
# 1. 工具注册表：工具名 → 真函数 + 给模型看的说明书
#    「说明书」会随每次请求发给模型；「真函数」留在本地，模型永远看不到
# ─────────────────────────────────────────────────────────────
def tool_get_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def tool_list_files(path="."):
    names = sorted(os.listdir(BASE))
    return "、".join(names[:14])


def tool_write_note(text="", path="demo_note.txt"):
    with open(os.path.join(BASE, path), "w", encoding="utf-8") as f:
        f.write(text)
    return f"已写入 {path}，{len(text)} 字"


TOOLS = {
    "get_time": {
        "schema": {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "获取当前本地日期与时间",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        "fn": tool_get_time,
    },
    "list_files": {
        "schema": {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "列出工作目录下的文件与子目录名",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "目录路径，默认工作目录根"},
                    },
                },
            },
        },
        "fn": tool_list_files,
    },
    "write_note": {
        "schema": {
            "type": "function",
            "function": {
                "name": "write_note",
                "description": "把一个文本备忘写进工作目录的文件",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string", "description": "要写入的内容"},
                        "path": {"type": "string", "description": "文件名"},
                    },
                    "required": ["text"],
                },
            },
        },
        "fn": tool_write_note,
    },
}


# ─────────────────────────────────────────────────────────────
# 2. "模型"：真实世界里，这个函数体是一次 HTTPS 请求
#    这里用规则顶替，方便离线跑通
# ─────────────────────────────────────────────────────────────
def fake_llm(messages, tools):
    last_user = next((m for m in reversed(messages) if m["role"] == "user"), None)
    saw_tool_result = any(m["role"] == "tool" for m in messages)
    available = [t["function"]["name"] for t in tools]

    if not saw_tool_result:
        text = last_user["content"]
        calls = []
        if ("时间" in text or "几点" in text) and "get_time" in available:
            calls.append({"id": "call_a1", "type": "function",
                          "function": {"name": "get_time", "arguments": "{}"}})
        if "文件" in text and "list_files" in available:
            calls.append({"id": "call_a2", "type": "function",
                          "function": {"name": "list_files", "arguments": '{"path": "."}'}})
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": calls,
            "stop_reason": "tool_calls" if calls else "end_turn",
        }

    observations = [m["content"] for m in messages if m["role"] == "tool"]
    return {
        "role": "assistant",
        "content": "查到了：" + "；".join(observations),
        "tool_calls": [],
        "stop_reason": "end_turn",
    }


# ─────────────────────────────────────────────────────────────
# 3. 主循环：这才是"框架"。全部逻辑就是下面这 20 行
# ─────────────────────────────────────────────────────────────
def run_agent(user_text, max_turns=6):
    messages = [
        {"role": "system", "content": "你是助手。需要外部信息或要动手时，调用工具，不要凭空编。"},
        {"role": "user", "content": user_text},
    ]
    tools = [t["schema"] for t in TOOLS.values()]

    for turn in range(1, max_turns + 1):
        print(f"\n{BAR}\n第 {turn} 轮 ▸ 发给模型的请求（messages 数组 = 唯一信道）\n{BAR}")
        print(json.dumps(messages, ensure_ascii=False, indent=2))
        print(f"\n（随请求一起发的工具说明书：{[t['function']['name'] for t in tools]}）")

        reply = fake_llm(messages, tools)
        print(f"\n{BAR}\n模型返回 ▸ stop_reason = {reply['stop_reason']}\n{BAR}")
        print(json.dumps({k: v for k, v in reply.items() if k != "stop_reason"},
                         ensure_ascii=False, indent=2))

        # 关键：stop_reason 是唯一的判断依据，框架不理解内容，只做分支
        if reply["stop_reason"] != "tool_calls":
            print(f"\n{BAR}\nstop_reason 不是 tool_calls ▸ 跳出循环，把回答交给用户\n{BAR}")
            return reply["content"]

        messages.append({k: v for k, v in reply.items() if k != "stop_reason"})

        for call in reply["tool_calls"]:
            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"] or "{}")
            print(f"\n  ▸ 框架收到调用请求：{name}({args})")

            if name not in TOOLS:                     # 模型可能编造不存在的工具
                result = f"错误：不存在名为 {name} 的工具"
                print(f"    ✗ 查表失败 ▸ {result}")
            else:
                fn = TOOLS[name]["fn"]                # ← 全部魔法就这一行：一次字典查找
                try:
                    result = str(fn(**args))
                    print(f"    ✓ 查表命中 ▸ 执行本地函数 ▸ 返回：{result[:70]}")
                except Exception as e:                # 参数写错、执行失败都要兜住
                    result = f"错误：{type(e).__name__}: {e}"
                    print(f"    ✗ 执行失败 ▸ {result}")

            messages.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "name": name,
                "content": result,
            })
            print(f"    ▸ 结果已追加进 messages（现在共 {len(messages)} 条），准备下一轮")

    return "（达到最大轮数，强制停止）"


if __name__ == "__main__":
    question = "现在几点了？顺便看看工作目录里有哪些文件。"
    print(f"{BAR}\n用户提问：{question}\n{BAR}")
    answer = run_agent(question)
    print(f"\n{BAR}\n最终回答 ▸ {answer}\n{BAR}")

    sys.stdout.write("\n\n── 换成真实 API，只有第一步要改 ──\n")
    print("""
def real_llm(messages, tools):
    resp = requests.post(
        "https://api.xxx.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "xxx", "messages": messages, "tools": tools},
    )
    data = resp.json()["choices"][0]
    return {"role": "assistant",
            "content": data["message"].get("content"),
            "tool_calls": data["message"].get("tool_calls", []),
            "stop_reason": data["finish_reason"]}   # 协议字段名各家略有不同
""")
