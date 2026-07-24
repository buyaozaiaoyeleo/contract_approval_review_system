"""合同字段 Repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract_field import ContractField
from app.repositories.base import BaseRepository


class ContractFieldRepository(BaseRepository[ContractField]):
    def __init__(self, db: AsyncSession):
        super().__init__(ContractField, db)

    async def get_by_document_id(self, document_id: int):
        return await self.get_by_field("document_id", document_id)
