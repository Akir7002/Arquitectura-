"""
Schemas (contratos de la API) para el recurso Usuario.

Se define un schema distinto por propósito, siguiendo el patrón oficial
de FastAPI (Base / Create / Update / Public):

- `UserBase`    -> campos comunes compartidos.
- `UserCreate`  -> lo que el cliente envía al registrarse (incluye password).
- `UserUpdate`  -> campos opcionales para una actualización parcial.
- `UserPublic`  -> lo que la API devuelve (NUNCA incluye la contraseña).

Esto evita accidentalmente serializar campos sensibles y le da a cada
endpoint un contrato de entrada/salida explícito y auto-documentado en
OpenAPI (Swagger UI en /docs).
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email único del usuario, usado como login.")
    full_name: str = Field(..., min_length=1, max_length=255, description="Nombre completo.")


class UserCreate(UserBase):
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Contraseña en texto plano (se hashea con Argon2 antes de persistir).",
    )


class UserUpdate(BaseModel):
    """Todos los campos son opcionales: soporta PATCH/PUT parcial."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    is_active: Optional[bool] = None


class UserPublic(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    # Permite construir el schema directamente desde el objeto ORM
    # (equivalente a `orm_mode = True` en Pydantic v1).
    model_config = ConfigDict(from_attributes=True)


class UserListResponse(BaseModel):
    """Envoltorio con metadatos de paginación (buena práctica REST)."""

    items: list[UserPublic]
    total: int
    page: int
    page_size: int
