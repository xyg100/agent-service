import json

# 读取 notebook 文件
with open(r'D:\Projects\pythonProjects\agent‑service\notebooks\day06\ToolCalling开发.ipynb', 'r', encoding='utf-8') as f:
    nb = json.load(f)

print("总单元格数:", len(nb['cells']))
for i, cell in enumerate(nb['cells']):
    cell_type = cell.get('cell_type')
    source = ''.join(cell.get('source', [])) if isinstance(cell.get('source'), list) else cell.get('source', '')
    print(f"单元格 {i}: type={cell_type}, 内容长度={len(source)}")
    if 'tools' in source:
        print("\n找到 tools:")
        print(source[:200])
        print("...")
