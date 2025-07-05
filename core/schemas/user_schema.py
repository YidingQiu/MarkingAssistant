from typing import Optional

from pydantic import BaseModel

from core.models import UserRole, User


class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.student


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole

    @staticmethod
    def from_user(user: User | None) -> Optional['UserResponse']:
        return UserResponse.model_validate(user.model_dump())
