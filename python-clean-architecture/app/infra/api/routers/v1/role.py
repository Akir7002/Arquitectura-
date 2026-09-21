from uuid import UUID

from fastapi import APIRouter, HTTPException

from app.core.dtos.role import CreateRoleRequest, RoleResponse, UpdateRole
from app.core.exceptions import (
    InvalidRoleError,
    RoleAlreadyExistsError,
    RoleNotFoundError,
)
from app.core.value_objects.id import InvalidIDError
from app.infra.api.dependencies.usecases.role import (
    CreateRole as CreateRoleUsecase,
    DeleteRole as DeleteRoleUsecase,
    GetRole as GetRoleUsecase,
    UpdateRole as UpdateRoleUsecase,
)

router = APIRouter()


@router.post("", status_code=201)
async def create(dto: CreateRoleRequest, usecase: CreateRoleUsecase) -> RoleResponse:
    try:
        return await usecase.execute(dto)
    except InvalidRoleError as error:
        raise HTTPException(status_code=400, detail=str(error))
    except RoleAlreadyExistsError:
        raise HTTPException(status_code=409, detail="Role already exists")


@router.get("/{role_id}")
async def get(role_id: UUID, usecase: GetRoleUsecase) -> RoleResponse:
    try:
        return await usecase.execute(str(role_id))
    except (InvalidIDError, RoleNotFoundError) as error:
        raise HTTPException(status_code=404, detail=str(error))


@router.patch("/{role_id}")
async def patch(
    role_id: UUID, dto: UpdateRole, usecase: UpdateRoleUsecase
) -> RoleResponse:
    try:
        return await usecase.execute(str(role_id), dto)
    except (InvalidRoleError, InvalidIDError) as error:
        raise HTTPException(status_code=400, detail=str(error))
    except RoleNotFoundError:
        raise HTTPException(status_code=404, detail="Role not found")


@router.delete("/{role_id}", status_code=204)
async def delete(role_id: UUID, usecase: DeleteRoleUsecase) -> None:
    try:
        if not await usecase.execute(str(role_id)):
            raise HTTPException(status_code=404, detail="Role not found")
    except InvalidIDError as error:
        raise HTTPException(status_code=400, detail=str(error))
