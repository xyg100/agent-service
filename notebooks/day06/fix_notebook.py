import json

# 读取 notebook 文件
notebook_path = r"D:\Projects\pythonProjects\agent‑service\notebooks\day06\ToolCalling开发.ipynb"

with open(notebook_path, 'r', encoding='utf-8') as f:
    nb = json.load(f)

# 遍历单元格找到 tools 定义并修复
for cell in nb['cells']:
    if cell.get('cell_type') == 'code':
        source = cell.get('source', [])
        if isinstance(source, list):
            code = ''.join(source)
        else:
            code = source
        
        # 查找包含 tools 定义的单元格
        if 'tools =' in code and '"name": "calculator"' in code:
            print("找到需要修复的单元格")
            # 解析新的 tools 定义
            new_tools = [
                {
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
                        "required": ["location"]
                    }
                },
                {
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
                        "required": ["x"],
                        "strict": True
                    }
                }
            ]
            
            # 构建新的单元格源代码
            new_source = """#2.=============定义tools列表,详细描述每个工具的参数信息=============
tools = """ + json.dumps(new_tools, indent=4, ensure_ascii=False) + """
"""
            cell['source'] = new_source.split('\n')
            cell['source'] = [line + '\n' for line in cell['source'][:-1]] + [cell['source'][-1]]
            break

# 保存修改后的 notebook
with open(notebook_path, 'w', encoding='utf-8') as f:
    json.dump(nb, f, ensure_ascii=False, indent=2)

print("Notebook 修复完成!")
