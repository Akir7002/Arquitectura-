from dataclasses import dataclass

from app.core.dtos.role import RoleResponse
from app.core.exceptions import RoleNotFoundError
from app.core.ports.role import RoleRepo
from app.core.value_objects.id import ID


@dataclass(frozen=True)
class GetRoleUsecase:
    role_repo: RoleRepo

    async def execute(self, role_id: str) -> RoleResponse:
        role = await self.role_repo.get_by_id(ID.from_string(role_id))
        if not role:
            raise RoleNotFoundError(f"Role with ID {role_id} not found")
        return RoleResponse(id=str(role.id), name=role.name, description=role.description)
