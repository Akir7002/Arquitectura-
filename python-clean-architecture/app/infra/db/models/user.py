from uuid import UUID

from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(primary_key=True)
    name: str
    email: str = Field(unique=True)
    password_hash: str
    role_id: UUID | None = Field(default=None, foreign_key="roles.id")
