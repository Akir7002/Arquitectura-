import pytest

from app.core.entities.role import Role
from app.core.exceptions import InvalidRoleError
from app.core.value_objects.id import ID


def test_role_requires_name():
    with pytest.raises(InvalidRoleError):
        Role(id=ID.generate(), name="   ")


def test_role_accepts_description():
    role = Role(id=ID.generate(), name="admin", description="Full access")

    assert role.name == "admin"
    assert role.description == "Full access"
