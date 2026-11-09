"""Schemas genéricos reutilizables en toda la API."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """
    Formato uniforme de error, expuesto en OpenAPI vía `responses={...}`
    en cada router. Mantener un formato de error consistente en toda la
    API es una recomendación estándar de diseño REST (ver también
    RFC 9457 "Problem Details for HTTP APIs" como referencia de estándar).
    """

    detail: str
