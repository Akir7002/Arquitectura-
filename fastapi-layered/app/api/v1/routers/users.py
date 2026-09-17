"""
Router: Usuarios (recurso protegido).

Aplica varias prácticas REST estándar:
- Verbos y códigos de estado HTTP correctos (201 al crear, 204 al borrar,
  404 si no existe, 403 si no autorizado).
- Paginación por query params (`page`, `page_size`) en la colección.
- `response_model` explícito en cada endpoint (nunca se devuelve el
  modelo ORM directamente) para no filtrar campos sensibles.
- Autorización a nivel de objeto (OWASP API1:2023 Broken Object Level
  Authorization): un usuario no-superusuario solo puede leer/editar su
  propio recurso.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_active_user, get_user_service
from app.core.exceptions import UserNotFoundError
from app.models.user import User
from app.schemas.common import ErrorResponse
from app.schemas.user import UserListResponse, UserPublic, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _ensure_self_or_superuser(current_user: User, target_user_id: int) -> None:
    """Autorización a nivel de objeto: dueño del recurso o superusuario."""
    if current_user.id != target_user_id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos sobre este recurso.",
        )


@router.get("/me", response_model=UserPublic, summary="Obtener el usuario autenticado actual")
async def read_current_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    return UserPublic.model_validate(current_user)


@router.get(
    "",
    response_model=UserListResponse,
    summary="Listar usuarios (paginado)",
)
async def list_users(
    service: Annotated[UserService, Depends(get_user_service)],
    _: Annotated[User, Depends(get_current_active_user)],
    page: Annotated[int, Query(ge=1, description="Número de página (1-indexado)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Tamaño de página (máx. 100)")] = 20,
) -> UserListResponse:
    users, total = await service.list_users(page=page, page_size=page_size)
    return UserListResponse(
        items=[UserPublic.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{user_id}",
    response_model=UserPublic,
    responses={404: {"model": ErrorResponse}},
    summary="Obtener un usuario por id",
)
async def get_user(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    _ensure_self_or_superuser(current_user, user_id)
    try:
        user = await service.get_by_id(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserPublic.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserPublic,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Actualizar (parcialmente) un usuario",
)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserPublic:
    _ensure_self_or_superuser(current_user, user_id)
    try:
        user = await service.update_user(user_id, payload)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return UserPublic.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
    summary="Eliminar un usuario",
)
async def delete_user(
    user_id: int,
    service: Annotated[UserService, Depends(get_user_service)],
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> None:
    _ensure_self_or_superuser(current_user, user_id)
    try:
        await service.delete_user(user_id)
    except UserNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
