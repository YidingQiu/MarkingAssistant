from enum import Enum
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship


class UserCourseRole(str, Enum):
    student = "student"
    teacher = "teacher"
    assistant = "assistant"

class UserCourse(SQLModel, table=True):
    __tablename__ = "user_course"
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True)
    course_id: Optional[int] = Field(default=None, foreign_key="course.id", primary_key=True)
    role: UserCourseRole = Field(default=UserCourseRole.student)

    user: 'User' = Relationship(back_populates="user_courses")
    course: 'Course' = Relationship(back_populates="user_courses")