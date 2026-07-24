"""合同文档 Repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_document import ContractDocument
from app.repositories.base import BaseRepository


class ContractDocumentRepository(BaseRepository[ContractDocument]):
    def __init__(self, db: AsyncSession):
        super().__init__(ContractDocument, db)

    async def get_by_doc_id(self, doc_id: str):
        return await self.get_by_field("doc_id", doc_id)

    async def get_by_md5(self, md5: str):
        return await self.get_by_field("file_md5", md5)

    async def list_by_approval_order(self, approval_order_id: int):
        return await self.get_all_by_field("approval_order_id", approval_order_id)

    async def get_all_by_field(self, field: str, value, limit: int = 100, offset: int = 0):
        from sqlalchemy import select

        result = await self.db.execute(
            select(self.model).where(getattr(self.model, field) == value).limit(limit).offset(offset)
        )
        return list(result.scalars().all())
