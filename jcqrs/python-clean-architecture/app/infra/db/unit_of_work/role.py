from app.infra.db import DBSession
from app.infra.db.repositories.role import RoleRepo
from app.infra.db.unit_of_work.base import BaseUnitOfWork


class RoleUnitOfWork(BaseUnitOfWork):
    def __init__(self, session: DBSession) -> None:
        super().__init__(session)
        self.role_repo = RoleRepo(session)


def role_uow_factory(session: DBSession) -> RoleUnitOfWork:
    return RoleUnitOfWork(session)
