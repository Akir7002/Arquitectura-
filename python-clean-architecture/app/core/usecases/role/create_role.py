from dataclasses import dataclass

from app.core.dtos.role import CreateRoleRequest, RoleResponse
from app.core.entities.role import Role
from app.core.exceptions import RoleAlreadyExistsError
from app.core.ports.role import RoleUnitOfWork
from app.core.value_objects.id import ID


@dataclass(frozen=True)
class CreateRoleUsecase:
    uow: RoleUnitOfWork

    async def execute(self, dto: CreateRoleRequest) -> RoleResponse:
        async with self.uow:
            if await self.uow.role_repo.get_by_name(dto.name):
                raise RoleAlreadyExistsError(f"Role with name {dto.name} already exists")

            role = Role(id=ID.generate(), name=dto.name, description=dto.description)
            await self.uow.role_repo.save(role)
            return RoleResponse(
                id=str(role.id), name=role.name, description=role.description
            )
