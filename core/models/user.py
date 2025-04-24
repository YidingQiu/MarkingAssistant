from enum import Enum
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    student = "student"
    tutor = "tutor"


class User(SQLModel, table=True):
    """User model represents a user in the system."""
    id: int = Field(default=None, primary_key=True)
    username: str
    email: str
    password: str
    role: UserRole = Field(default=UserRole.student)  # student, tutor