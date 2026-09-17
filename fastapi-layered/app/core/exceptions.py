"""
Excepciones de dominio (Core).

Se definen excepciones propias de la capa de negocio, desacopladas de
FastAPI/HTTP. Las capas de servicio y repositorio lanzan estas excepciones;
la capa de API (routers) es la única responsable de traducirlas a
`HTTPException` con el código de estado adecuado (ver app/api/v1/routers).

Esto mantiene la regla de dependencia de una arquitectura en capas:
las capas internas (dominio/servicios) no conocen detalles de HTTP.
"""


class DomainError(Exception):
    """Excepción base para errores de negocio."""


class UserAlreadyExistsError(DomainError):
    """Se intentó registrar un usuario con un email ya existente."""


class UserNotFoundError(DomainError):
    """El usuario solicitado no existe."""


class InvalidCredentialsError(DomainError):
    """Email o contraseña incorrectos al autenticar."""


class InactiveUserError(DomainError):
    """El usuario existe pero está deshabilitado."""
