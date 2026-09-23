from typing import Optional

from sqlmodel import select

from app.core.entities.role import Role
from app.core.ports.role import RoleRepo as RoleRepoPort
from app.core.value_objects.id import ID
from app.infra.db import DBSession
from app.infra.db.models.role import Role as DBRole


class RoleRepo(RoleRepoPort):
    def __init__(self, session: DBSession) -> None:
        self.session = session

    async def save(self, role: Role) -> None:
        self.session.add(
            DBRole(id=role.id.value, name=role.name, description=role.description)
        )

    async def get_by_id(self, _id: ID) -> Optional[Role]:
        db_role = await self.session.get(DBRole, _id.value)
        return self._to_entity(db_role) if db_role else None

    async def get_by_name(self, name: str) -> Optional[Role]:
        result = await self.session.exec(select(DBRole).where(DBRole.name == name))
        db_role = result.first()
        return self._to_entity(db_role) if db_role else None

    async def delete(self, _id: ID) -> bool:
        db_role = await self.session.get(DBRole, _id.value)
        if not db_role:
            return False
        await self.session.delete(db_role)
        return True

    async def update(self, role: Role) -> Optional[Role]:
        db_role = await self.session.get(DBRole, role.id.value)
        if not db_role:
            return None
        db_role.name = role.name
        db_role.description = role.description
        self.session.add(db_role)
        return role

    @staticmethod
    def _to_entity(db_role: DBRole) -> Role:
        return Role(
            id=ID.from_string(str(db_role.id)),
            name=db_role.name,
            description=db_role.description,
        )
