import json

# 读取 notebook 文件
with open(r'D:\Projects\pythonProjects\agent‑service\notebooks\day06\ToolCalling开发.ipynb', 'r', encoding='utf-8') as f:
    data = json.load(f)

print("单元格数量:", len(data['cells']))
for i, cell in enumerate(data['cells']):
    if cell.get('cell_type') == 'code':
        source = ''.join(cell.get('source', []))
        if 'tools' in source and ('get_weather' in source or 'calculator' in source or 'square_root' in source):
            print(f"\n找到 tools 定义的单元格 {i}:")
            print(source)
            print("="*80)
