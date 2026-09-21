from typing import Annotated, AsyncGenerator

from fastapi import Depends

from app.core.ports import role
from app.infra.db import async_session
from app.infra.db.repositories.role import RoleRepo
from app.infra.db.unit_of_work.role import RoleUnitOfWork, role_uow_factory


async def get_role_repo() -> AsyncGenerator[role.RoleRepo, None]:
    async with async_session() as session:
        yield RoleRepo(session)


async def get_role_uow() -> AsyncGenerator[role.RoleUnitOfWork, None]:
    async with async_session() as session:
        yield role_uow_factory(session)


Repo = Annotated[role.RoleRepo, Depends(get_role_repo)]
UnitOfWork = Annotated[role.RoleUnitOfWork, Depends(get_role_uow)]
