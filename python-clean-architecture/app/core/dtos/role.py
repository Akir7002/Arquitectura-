from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, kw_only=True)
class CreateRoleRequest:
    name: str
    description: str = ""


@dataclass(frozen=True, kw_only=True)
class UpdateRole:
    name: Optional[str] = None
    description: Optional[str] = None

    def __post_init__(self):
        if self.name is None and self.description is None:
            raise ValueError("At least one field must be provided")


@dataclass(frozen=True, kw_only=True)
class RoleResponse:
    id: str
    name: str
    description: str
