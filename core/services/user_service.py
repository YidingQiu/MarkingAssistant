from typing import Optional
from sqlmodel import Session, select
from core.models.user import User
from core.configs.database import get_db
from fastapi import Depends

from core.schemas.user_schema import UserCreateRequest


def create_user(user_req: UserCreateRequest, db: Session = Depends(get_db)) -> User:
    user = User(**user_req.dict())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(user_id: int, db: Session = Depends(get_db)) -> Optional[User]:
    return db.get(User, user_id)


def get_user_by_username(username: str, db: Session = Depends(get_db)) -> Optional[User]:
    statement = select(User).where(User.username == username)
    result = db.exec(statement).first()
    return result