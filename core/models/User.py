from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    """User model represents a user in the system."""
    id: int = Field(default=None, primary_key=True)
    username: str
    email: str
    password: str
    role: str = Field(default="student")  # student, teacher, admin