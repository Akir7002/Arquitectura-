"""
Base declarativa de SQLAlchemy 2.0.

Todos los modelos ORM (app/models/*.py) heredan de esta clase para que
`Base.metadata` los conozca y puedan crearse/migrarse como conjunto.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
