from typing import Optional
from sqlmodel import SQLModel, Field, Relationship

class Course(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    short_name: str
    faculty: str

    user_courses: list['UserCourse'] = Relationship(back_populates="course")