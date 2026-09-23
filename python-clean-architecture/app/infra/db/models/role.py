from uuid import UUID

from sqlmodel import Field, SQLModel


class Role(SQLModel, table=True):
    __tablename__ = "roles"

    id: UUID = Field(primary_key=True)
    name: str = Field(unique=True, index=True)
    description: str = ""
