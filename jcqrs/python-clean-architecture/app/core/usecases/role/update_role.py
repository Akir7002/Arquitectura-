from dataclasses import dataclass

from app.core.dtos.role import RoleResponse, UpdateRole
from app.core.entities.role import Role
from app.core.exceptions import RoleNotFoundError
from app.core.ports.role import RoleUnitOfWork
from app.core.value_objects.id import ID


@dataclass(frozen=True)
class UpdateRoleUsecase:
    uow: RoleUnitOfWork

    async def execute(self, role_id: str, dto: UpdateRole) -> RoleResponse:
        role_id_value = ID.from_string(role_id)
        async with self.uow:
            current = await self.uow.role_repo.get_by_id(role_id_value)
            if not current:
                raise RoleNotFoundError(f"Role with ID {role_id} not found")

            role = Role(
                id=current.id,
                name=dto.name if dto.name is not None else current.name,
                description=(
                    dto.description
                    if dto.description is not None
                    else current.description
                ),
            )
            updated = await self.uow.role_repo.update(role)
            if not updated:
                raise RoleNotFoundError(f"Role with ID {role_id} not found")
            return RoleResponse(
                id=str(updated.id),
                name=updated.name,
                description=updated.description,
            )
