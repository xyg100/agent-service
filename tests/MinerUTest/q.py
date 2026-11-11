from pathlib import Path

from mineru import MinerU

# 用 pathlib 拼路径，避免 Windows 路径里的反斜杠被当成转义序列
# 原来直接写 "D:\Projects\...\agent-service\..." 时，\a 被解析成了 BEL 字符（\x07）
ROOT = Path(__file__).resolve().parents[2]  # agent-service/
SOURCE = ROOT / "notebooks" / "day10" / "resources" / "贵州茅台研报.pdf"
OUTPUT = ROOT / "111.md"

mineru = MinerU(token="sk-BHpeGz4XpTn8BiLwnAqxRCZVaXS6isGeLKyZzxkE2Kp0EPG3")
result = mineru.extract(source=str(SOURCE), ocr=True)
result.save_markdown(str(OUTPUT), with_images=True)



