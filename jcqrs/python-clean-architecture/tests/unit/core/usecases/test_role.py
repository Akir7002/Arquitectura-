from unittest.mock import AsyncMock, MagicMock

from app.core.dtos.role import CreateRoleRequest
from app.core.usecases.role.create_role import CreateRoleUsecase


async def test_create_role():
    repo = MagicMock()
    repo.get_by_name = AsyncMock(return_value=None)
    repo.save = AsyncMock()
    uow = MagicMock()
    uow.role_repo = repo
    uow.__aenter__ = AsyncMock(return_value=uow)
    uow.__aexit__ = AsyncMock(return_value=None)

    result = await CreateRoleUsecase(uow).execute(
        CreateRoleRequest(name="admin", description="Full access")
    )

    assert result.name == "admin"
    assert result.description == "Full access"
    repo.save.assert_awaited_once()
