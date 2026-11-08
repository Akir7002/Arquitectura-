from dataclasses import dataclass

from app.core.ports.role import RoleRepo
from app.core.value_objects.id import ID


@dataclass(frozen=True)
class DeleteRoleUsecase:
    role_repo: RoleRepo

    async def execute(self, role_id: str) -> bool:
        return await self.role_repo.delete(ID.from_string(role_id))
