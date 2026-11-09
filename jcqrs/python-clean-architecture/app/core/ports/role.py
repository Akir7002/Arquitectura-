from typing import Optional, Protocol

from app.core.entities.role import Role
from app.core.ports.unit_of_work import UnitOfWork
from app.core.value_objects.id import ID


class RoleRepo(Protocol):
    async def save(self, role: Role) -> None: ...

    async def get_by_id(self, _id: ID) -> Optional[Role]: ...

    async def get_by_name(self, name: str) -> Optional[Role]: ...

    async def delete(self, _id: ID) -> bool: ...

    async def update(self, role: Role) -> Optional[Role]: ...


class RoleUnitOfWork(UnitOfWork, Protocol):
    role_repo: RoleRepo
