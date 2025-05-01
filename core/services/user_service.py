from typing import Optional, List
from sqlmodel import Session, select

from core.models import User
from core.schemas.user_schema import UserCreateRequest, UserResponse


def create_user(user_req: UserCreateRequest, db: Session) -> UserResponse:
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
