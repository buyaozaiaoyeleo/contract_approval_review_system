"""Repository 基类封装"""

from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.response import PageResult

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """通用 Repository 基类，提供 CRUD 和分页能力

    所有专属 Repository 继承此类，自动获得标准查询方法。
    子类可按需添加业务特有查询方法。
    """

    def __init__(self, model: type[ModelType], db: AsyncSession):
        self.model = model
        self.db = db

    # ==================== 查询 ====================

    async def get_by_id(self, id_val: int) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(self.model.id == id_val))
        return result.scalar_one_or_none()

    async def get_by_field(self, field: str, value: Any) -> ModelType | None:
        result = await self.db.execute(select(self.model).where(getattr(self.model, field) == value))
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[ModelType]:
        result = await self.db.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all())

    async def list_by_ids(self, ids: list[int]) -> list[ModelType]:
        if not ids:
            return []
        result = await self.db.execute(select(self.model).where(self.model.id.in_(ids)))
        return list(result.scalars().all())

    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        where_conditions: list[Any] | None = None,
        order_by: Any | None = None,
    ) -> PageResult[ModelType]:
        conditions = where_conditions or []

        # 先查询总数
        count_query = select(func.count()).select_from(self.model)
        if conditions:
            count_query = count_query.where(*conditions)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # 再查询分页数据
        items_query = select(self.model)
        if conditions:
            items_query = items_query.where(*conditions)
        if order_by is not None:
            items_query = items_query.order_by(order_by)
        items_query = items_query.limit(page_size).offset((page - 1) * page_size)
        result = await self.db.execute(items_query)
        items = list(result.scalars().all())

        return PageResult.of(items=items, page=page, page_size=page_size, total=total)

    # ==================== 写入 ====================

    async def create(self, instance: ModelType) -> ModelType:
        self.db.add(instance)
        await self.db.flush()       # 立即刷出以获取自增/默认值
        return instance

    async def bulk_create(self, instances: list[ModelType]) -> list[ModelType]:
        self.db.add_all(instances)
        await self.db.flush()
        return instances

    async def update(self, instance: ModelType) -> ModelType:
        await self.db.merge(instance)       # merge 处理已存在对象
        await self.db.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        await self.db.delete(instance)
        await self.db.flush()

    async def delete_by_id(self, id_val: int) -> bool:
        instance = await self.get_by_id(id_val)
        if instance is None:
            return False
        await self.db.delete(instance)
        await self.db.flush()
        return True

    # ==================== 辅助 ====================

    async def exists(self, field: str, value: Any) -> bool:
        result = await self.db.execute(
            select(func.count()).select_from(self.model).where(
                getattr(self.model, field) == value
            )
        )
        count = result.scalar() or 0
        return count > 0

    async def count(self, where_conditions: list[Any] | None = None) -> int:
        query = select(func.count()).select_from(self.model)
        if where_conditions:
            query = query.where(*where_conditions)
        result = await self.db.execute(query)
        return result.scalar() or 0
