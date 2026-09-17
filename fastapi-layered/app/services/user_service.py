"""
Servicio de Usuario (capa de lógica de negocio).

Aquí viven las reglas de negocio: validar que un email no esté duplicado,
decidir cómo se hashea una contraseña, verificar credenciales, emitir el
JWT, etc. El servicio orquesta al repositorio pero no conoce detalles de
HTTP (no lanza HTTPException; lanza excepciones de dominio definidas en
app/core/exceptions.py). Es la capa que los routers (API) invocan.
"""

from app.core.exceptions import (
    InactiveUserError,
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    async def register(self, data: UserCreate) -> User:
        """Registra un nuevo usuario, validando unicidad de email."""
        existing = await self._repository.get_by_email(data.email)
        if existing is not None:
            raise UserAlreadyExistsError(f"El email '{data.email}' ya está registrado.")

        hashed = hash_password(data.password)
        return await self._repository.create(
            email=data.email, full_name=data.full_name, hashed_password=hashed
        )

    async def authenticate(self, email: str, password: str) -> User:
        """
        Valida credenciales y devuelve el usuario autenticado.

        Nota de seguridad: se usa un mensaje de error genérico e idéntico
        tanto si el usuario no existe como si la contraseña es incorrecta,
        para no dar pistas a un atacante (mitigación de enumeración de
        usuarios, alineado con OWASP API2:2023 Broken Authentication).
        """
        user = await self._repository.get_by_email(email)
        password_ok = verify_password(password, user.hashed_password if user else None)

        if user is None or not password_ok:
            raise InvalidCredentialsError("Email o contraseña incorrectos.")
        if not user.is_active:
            raise InactiveUserError("El usuario está deshabilitado.")
        return user

    def create_token_for_user(self, user: User) -> str:
        return create_access_token(subject=str(user.id))

    async def get_by_id(self, user_id: int) -> User:
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError(f"Usuario con id={user_id} no encontrado.")
        return user

    async def list_users(self, *, page: int, page_size: int) -> tuple[list[User], int]:
        offset = (page - 1) * page_size
        users, total = await self._repository.list(offset=offset, limit=page_size)
        return list(users), total

    async def update_user(self, user_id: int, data: UserUpdate) -> User:
        user = await self.get_by_id(user_id)
        hashed = hash_password(data.password) if data.password else None
        return await self._repository.update(user, data, hashed)

    async def delete_user(self, user_id: int) -> None:
        user = await self.get_by_id(user_id)
        await self._repository.delete(user)
