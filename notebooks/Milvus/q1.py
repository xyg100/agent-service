from langchain_text_splitters import MarkdownHeaderTextSplitter
def prepare_docs():
    # =============1.准备文档================
    with open('./评估.md', 'r', encoding='utf-8') as f:
        doc = f.read()

    # =============2.切分文档================
    # 切分依据，这里是按照三级标题
    # 遇到  # 开头的行，就把文字记到 metadata 的 h1 键里
    headers_to_split_on = [
        ("#", "h1"),
        ("##", "h2"),
        ("###", "h3"),
    ]

    # 创建切分器
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on,
        strip_headers =  False  # 在正文中是否去除标题，False，不去除
    )

if __name__ == '__main__':
    prepare_docs()