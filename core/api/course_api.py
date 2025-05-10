from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from core.configs.database import get_db
from core.models import Course, UserCourse, User, UserCourseRole
from core.services import user_course_service  # Your service module

router = APIRouter(prefix="/course", tags=["UserCourse"])


@router.get("/all", response_model=List[Course])
def list_all(db: Session = Depends(get_db)):
    return user_course_service.list_all(db)

@router.get("/user/{user_id}", response_model=List[Course])
def list_courses_by_user_id(user_id: int, db: Session = Depends(get_db)):
    return user_course_service.list_courses_by_userid(user_id, db)


@router.post("/register", response_model=UserCourse)
def create_user_course(
    user_id: int,
    course_id: int,
    role: UserCourseRole = UserCourseRole.student,
    db: Session = Depends(get_db)
):
    return user_course_service.create_user_course(db, user_id, course_id, role)


@router.get("/{course_id}", response_model=Course)
def get_course(course_id: int, db: Session = Depends(get_db)):
    return user_course_service.get_course(db, course_id)


@router.get("/{course_id}/users", response_model=List[User])
def list_users_by_course_id(course_id: int, db: Session = Depends(get_db)):
    return user_course_service.list_users_by_course_id(db, course_id)
