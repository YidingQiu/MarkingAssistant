from typing import Optional, List
from sqlmodel import Session, select

from core.auth.auth_handler import get_password_hash
from core.models import User, Course, UserCourse, UserCourseRole, UserRole
from core.schemas.user_schema import UserCreateRequest, UserResponse, UserSetupRequest


def create_user(user_req: UserCreateRequest, db: Session) -> UserResponse:
    user_req.password = get_password_hash(user_req.password)
    user = User(**user_req.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.from_user(user)


def get_user(user_id: int, db: Session) -> Optional[UserResponse]:
    return UserResponse.from_user(db.get(User, user_id))


def get_user_by_username(username: str, db: Session) -> Optional[UserResponse]:
    statement = select(User).where(User.username == username)
    result = db.exec(statement).first()
    return UserResponse.from_user(result)

def list_users(db: Session) -> List[UserResponse]:
    statement = select(User)
    users = db.exec(statement).all()
    return [UserResponse.from_user(user) for user in users]


def setup_user(current_user, req: UserSetupRequest, db):
    statement = select(User).where(User.username == current_user.username)
    user = db.exec(statement).first()
    if not user:
        raise ValueError(f"User {current_user} not found")

    # Update user fields
    user.role = req.role
    user.notify_updates = req.notify_updates
    db.add(user)

    # Create a new course related to the user
    course = Course(
        name=req.course_name,
        short_name=req.course_short_name,
        faculty=req.course_faculty
    )
    db.add(course)
    db.commit()  # Commit to get course.id populated
    db.refresh(course)

    # Create linking UserCourse record
    course_role = UserCourseRole.student if req.role == UserRole.student else UserCourseRole.teacher
    user_course = UserCourse(user_id=user.id, course_id=course.id, role=course_role)
    db.add(user_course)

    db.commit()
    db.refresh(user)

    return user