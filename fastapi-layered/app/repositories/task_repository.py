from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskUpdate


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, task_id: int, owner_id: int) -> Optional[Task]:
        result = await self._session.execute(
            select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self, *, owner_id: int, offset: int = 0, limit: int = 20
    ) -> tuple[Sequence[Task], int]:
        items_result = await self._session.execute(
            select(Task)
            .where(Task.owner_id == owner_id)
            .order_by(Task.id)
            .offset(offset)
            .limit(limit)
        )
        total_result = await self._session.execute(
            select(func.count()).select_from(Task).where(Task.owner_id == owner_id)
        )
        return items_result.scalars().all(), total_result.scalar_one()

    async def create(
        self, *, owner_id: int, title: str, description: str | None
    ) -> Task:
        task = Task(owner_id=owner_id, title=title, description=description)
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def update(self, task: Task, data: TaskUpdate) -> Task:
        changes = data.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(task, field, value)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self._session.delete(task)
        await self._session.flush()
