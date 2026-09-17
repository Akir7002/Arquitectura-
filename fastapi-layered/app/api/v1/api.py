"""
Agregador de routers de la versión v1 de la API.

Centralizar el `include_router` aquí (en vez de en `main.py`) hace que
agregar una nueva versión (v2) sea tan simple como crear
`app/api/v2/api.py` sin tocar el resto de la aplicación, siguiendo la
práctica de versionado de API por prefijo de URL.
"""

from fastapi import APIRouter

from app.api.v1.routers import auth, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
