from uuid import UUID

from sqlalchemy import ARRAY, BigInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.common.models import Base, CreateAtMixin


class ParentChunk(Base, CreateAtMixin):
    """父知识块"""

    __tablename__ = "parent_chunks"

    # Id
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
    )
    # 产品Id
    product_id: Mapped[int] = mapped_column(BigInteger)
    # 条款名称
    clause_name: Mapped[str] = mapped_column(String(300))
    # 章节路径
    section_path: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=list,
    )
    # 内容
    content: Mapped[str] = mapped_column(Text)