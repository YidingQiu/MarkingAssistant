from fastapi import Depends
from sqlmodel import SQLModel, create_engine, Session

from core.configs.settings import settings

DATABASE_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_URL}:{settings.DB_PORT}/marking"

engine = create_engine(DATABASE_URL, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session