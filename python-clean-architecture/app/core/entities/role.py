from dataclasses import dataclass

from app.core.exceptions import InvalidRoleError
from app.core.value_objects.id import ID


@dataclass(frozen=True, kw_only=True)
class Role:
    id: ID
    name: str
    description: str = ""

    def __post_init__(self):
        if not self.name or not self.name.strip():
            raise InvalidRoleError("Role name cannot be empty")
