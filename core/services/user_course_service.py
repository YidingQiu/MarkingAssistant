from typing import List, Optional
from fastapi import HTTPException
from sqlmodel import Session, select

from core.models import Course, UserCourse, UserCourseRole, User

def list_all(db: Session) -> List[Course]:
    statement = select(Course)
    courses = db.exec(statement).all()
    return courses

def list_courses_by_userid(user_id: int, db: Session) -> List[Course]:
    statement = select(Course).join(UserCourse).where(UserCourse.user_id == user_id)
    courses = db.exec(statement).all()
    return courses


def create_user_course(db: Session, user_id: int, course_id: int, role: Optional[UserCourseRole] = UserCourseRole.student) -> UserCourse:
    user_course = UserCourse(user_id=user_id, course_id=course_id, role=role)
    db.add(user_course)
    db.commit()
    db.refresh(user_course)
    return user_course


def get_course(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def list_users_by_course_id(db: Session, course_id: int) -> List[User]:
    statement = select(User).join(UserCourse).where(UserCourse.course_id == course_id)
    users = db.exec(statement).all()
    return users
