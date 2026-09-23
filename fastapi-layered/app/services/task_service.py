from app.core.exceptions import UserNotFoundError
from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    async def create_task(self, owner_id: int, data: TaskCreate) -> Task:
        return await self._repository.create(
            owner_id=owner_id, title=data.title, description=data.description
        )

    async def get_by_id(self, task_id: int, owner_id: int) -> Task:
        task = await self._repository.get_by_id(task_id, owner_id)
        if task is None:
            raise UserNotFoundError(f"Tarea con id={task_id} no encontrada.")
        return task

    async def get_public_by_id(self, task_id: int) -> Task:
        task = await self._repository.get_public_by_id(task_id)
        if task is None:
            raise UserNotFoundError(f"Tarea con id={task_id} no encontrada.")
        return task

    async def list_tasks(
        self, *, owner_id: int, page: int, page_size: int
    ) -> tuple[list[Task], int]:
        offset = (page - 1) * page_size
        tasks, total = await self._repository.list(
            owner_id=owner_id, offset=offset, limit=page_size
        )
        return list(tasks), total

    async def list_public_tasks(
        self, *, page: int, page_size: int
    ) -> tuple[list[Task], int]:
        offset = (page - 1) * page_size
        tasks, total = await self._repository.list_public(offset=offset, limit=page_size)
        return list(tasks), total

    async def update_task(self, task_id: int, owner_id: int, data: TaskUpdate) -> Task:
        task = await self.get_by_id(task_id, owner_id)
        return await self._repository.update(task, data)

    async def delete_task(self, task_id: int, owner_id: int) -> None:
        task = await self.get_by_id(task_id, owner_id)
        await self._repository.delete(task)
