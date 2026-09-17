"""
Router: Autenticación.

Capa API (presentación): solo se encarga de HTTP -- recibe la petición,
la valida con el schema Pydantic, invoca al servicio, y traduce las
excepciones de dominio a códigos de estado HTTP. No contiene lógica de
negocio.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import get_user_service
from app.core.exceptions import InactiveUserError, InvalidCredentialsError, UserAlreadyExistsError
from app.schemas.auth import Token
from app.schemas.common import ErrorResponse
from app.schemas.user import UserCreate, UserPublic
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    responses={409: {"model": ErrorResponse, "description": "El email ya está registrado"}},
)
async def register(
    payload: UserCreate,
    service: Annotated[UserService, Depends(get_user_service)],
) -> UserPublic:
    try:
        user = await service.register(payload)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return UserPublic.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Iniciar sesión y obtener un token JWT",
    responses={401: {"model": ErrorResponse, "description": "Credenciales inválidas"}},
)
async def login(
    # OAuth2PasswordRequestForm es el formulario estándar (RFC 6749) que
    # además hace que Swagger UI muestre el flujo de login "password".
    # El estándar usa el campo `username`; aquí se recibe el email en él.
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: Annotated[UserService, Depends(get_user_service)],
) -> Token:
    try:
        user = await service.authenticate(form_data.username, form_data.password)
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    access_token = service.create_token_for_user(user)
    return Token(access_token=access_token)
