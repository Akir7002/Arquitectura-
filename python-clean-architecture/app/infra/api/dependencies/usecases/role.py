from typing import Annotated

from fastapi import Depends

from app.core.usecases.role import (
    CreateRoleUsecase,
    DeleteRoleUsecase,
    GetRoleUsecase,
    UpdateRoleUsecase,
)
from app.infra.api.dependencies.role import Repo, UnitOfWork


def get_create_role_usecase(uow: UnitOfWork) -> CreateRoleUsecase:
    return CreateRoleUsecase(uow)


def get_get_role_usecase(repo: Repo) -> GetRoleUsecase:
    return GetRoleUsecase(repo)


def get_update_role_usecase(uow: UnitOfWork) -> UpdateRoleUsecase:
    return UpdateRoleUsecase(uow)


def get_delete_role_usecase(repo: Repo) -> DeleteRoleUsecase:
    return DeleteRoleUsecase(repo)


CreateRole = Annotated[CreateRoleUsecase, Depends(get_create_role_usecase)]
GetRole = Annotated[GetRoleUsecase, Depends(get_get_role_usecase)]
UpdateRole = Annotated[UpdateRoleUsecase, Depends(get_update_role_usecase)]
DeleteRole = Annotated[DeleteRoleUsecase, Depends(get_delete_role_usecase)]
