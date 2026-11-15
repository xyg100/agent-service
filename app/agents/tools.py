from langchain_core.tools import tool


@tool
async def query_candidate_products(
        category: str | None = None,
) -> str:
    """查询当前可售的候选保险产品列表。

    Args:
        category: 保险产品类别，例如"医疗险""重疾险""意外险""寿险"。不确定时不要传，返回全部类别。
    """
    from app.infra.database import AsyncSessionFactory
    from app.modules.product.service import ProductService

    async with AsyncSessionFactory() as session:
        products = await ProductService(session).list_products(category)

    if not products:
        return "没有查询到候选保险产品。"

    return "\n\n".join(
        f"产品ID：{product.id}\n"
        f"名称：{product.name}\n"
        f"类别：{product.category}\n"
        f"保险公司：{product.insurer}\n"
        f"保费范围：{product.min_premium} ~ {product.max_premium}\n"
        f"适用人群：{product.target_group}\n"
        f"产品亮点：{'、'.join(product.highlights or [])}\n"
        f"条款名称：{product.clause_name}\n"
        f"产品简介：{product.description}"
        for product in products
    )


@tool
async def query_product_clause(
        query: str,
        k: int,
        product_id: int,
) -> str:
    """查询指定保险产品的条款内容。

    Args:
        query: 需要从保险条款中查询的问题。
        product_id: 保险产品ID。
    """
    from app.rag import retriever

    chunks = await retriever.retrieve(query, k, product_id)
    if not chunks:
        return "没有查询到相关保险条款。"

    return "\n\n".join(
        f"章节：{' > '.join(chunk.section_path)}\n"
        f"内容：{chunk.content}"
        for chunk in chunks
    )
