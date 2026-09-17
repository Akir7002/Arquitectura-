"""
Capa de seguridad (Core).

Implementa las dos primitivas de seguridad que usa la capa de servicios:

1. Hashing de contraseñas con `pwdlib` (Argon2), la librería recomendada
   actualmente por la documentación oficial de FastAPI:
   https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
   Argon2 es el ganador de la Password Hashing Competition y es resistente
   a ataques por GPU/ASIC, cumpliendo OWASP ASVS 2.4 (Password Storage).

2. Creación y verificación de JSON Web Tokens (JWT) con `pyjwt`, siguiendo
   el estándar OAuth2 "Bearer Token" (RFC 6750) usado por FastAPI en su
   flujo `OAuth2PasswordBearer`.

Buenas prácticas de seguridad aplicadas (OWASP API Security Top 10 2023):
- API2:2023 Broken Authentication -> tokens firmados, con expiración corta
  y verificación estricta del algoritmo.
- Prevención de ataques de temporización: se verifica un hash "dummy"
  cuando el usuario no existe, para que el tiempo de respuesta no filtre
  si un email está o no registrado.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()

# PasswordHash.recommended() usa Argon2 con parámetros seguros por defecto.
password_hash = PasswordHash.recommended()

# Hash "señuelo" precalculado, usado solo para igualar tiempos de respuesta
# cuando el usuario no existe (mitigación de timing attacks).
_DUMMY_HASH = password_hash.hash("dummy-password-for-timing-safety")


def hash_password(plain_password: str) -> str:
    """Genera el hash Argon2 de una contraseña en texto plano."""
    return password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: Optional[str]) -> bool:
    """
    Verifica una contraseña contra su hash.

    Si `hashed_password` es None (usuario inexistente), igual se ejecuta
    una verificación contra un hash señuelo para no revelar, por el tiempo
    de respuesta, si el usuario existe o no.
    """
    if hashed_password is None:
        password_hash.verify(plain_password, _DUMMY_HASH)
        return False
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    """
    Crea un JWT firmado (HS256) con claims estándar:
    - `sub`: identificador del usuario (subject, RFC 7519).
    - `exp`: expiración (obligatoria para limitar la ventana de robo de token).
    - `iat`: momento de emisión, útil para auditoría/revocación.
    """
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))

    to_encode: dict[str, Any] = {"sub": subject, "iat": now, "exp": expire}
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodifica y valida un JWT.

    Lanza `jwt.PyJWTError` (o subclases como `ExpiredSignatureError`,
    `InvalidTokenError`) si el token es inválido, está expirado o fue
    firmado con un algoritmo distinto al esperado. El algoritmo se fija
    explícitamente (`algorithms=[...]`) para evitar el ataque conocido
    "alg confusion" (JWT sin restricción de algoritmo).
    """
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
