from pydantic import BaseModel

from core.models.user import UserRole


class UserCreateRequest(BaseModel):
    username: str
    email: str
    password: str
    role: UserRole = UserRole.student
