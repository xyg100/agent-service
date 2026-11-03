import json

# 读取 notebook 文件
with open(r'D:\Projects\pythonProjects\agent‑service\notebooks\day06\ToolCalling开发.ipynb', 'r', encoding='utf-8') as f:
    data = json.load(f)

# 获取第2个单元格（tools 定义）
cell_source = data['cells'][2]['source']
print("原始内容:")
print(''.join(cell_source))
print("\n" + "="*80 + "\n")

# 合并单元格的源代码
full_source = ''.join(cell_source)

# 执行替换
new_source = '''#%%
#2.=============定义tools列表,详细描述每个工具的参数信息=============
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get weather information for a specific location",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The location to check the weather for"
                    }
                },
                "required": [
                    "location"
                ]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "A simple calculator tool",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "number",
                        "description": "The number to calculate the square root of"
                    }
                },
                "required": [
                    "x"
                ],
                "strict": true
            }
        }
    }
]
'''

# 替换
data['cells'][2]['source'] = new_source

# 写回文件
with open(r'D:\Projects\pythonProjects\agent‑service\notebooks\day06\ToolCalling开发.ipynb', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print("修复完成！")
print("\n新内容:")
print(new_source)
