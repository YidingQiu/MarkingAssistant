from enum import Enum
from sqlmodel import Field, SQLModel, Relationship

class UserRole(str, Enum):
    student = "student"
    tutor = "tutor"
    admin = "admin"

class LoginType(str, Enum):
    userpass = "userpass"
    google = "google"


class User(SQLModel, table=True):
    """User model represents a user in the system."""
    id: int = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    email: str = Field(unique=True)
    password: str = Field(exclude=True)
    role: UserRole = Field(default=UserRole.student)  # student, tutor
    login_type: LoginType

    user_courses: list['UserCourse'] = Relationship(back_populates="user")