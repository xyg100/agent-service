from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.rag.models import ParentChunk


class ParentChunkRepository:

    def __init__(self, session: AsyncSession):
        self.session = session

    async def delete_by_product_id(self, product_id: int) -> None:
        await self.session.execute(
            delete(ParentChunk).where(
                ParentChunk.product_id == product_id
            )
        )

    def add_all(self, parent_chunks: list[ParentChunk]) -> None:
        self.session.add_all(parent_chunks)