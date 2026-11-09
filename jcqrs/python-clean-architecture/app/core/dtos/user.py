from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True, kw_only=True)
class CreateUserRequest:
    name: str
    email: str
    password: str
    role_id: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class UserResponse:
    id: str
    name: str
    email: str
    role_id: Optional[str] = None


@dataclass(frozen=True)
class UpdateUser:
    name: Optional[str] = None
    email: Optional[str] = None
    role_id: Optional[str] = None

    def __post_init__(self):
        if self.name is None and self.email is None and self.role_id is None:
            raise ValueError("At least one field must be provided")
