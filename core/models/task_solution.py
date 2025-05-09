from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy import Column
from sqlmodel import SQLModel, Field, JSON, Relationship

class TaskSolution(SQLModel, table=True):
    __tablename__ = "task_solution"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    task_id: int = Field(foreign_key="task.id")
    date: datetime = Field(default_factory=datetime.utcnow)
    file_url: str | None
    score: Optional[float]
    scoring_version: Optional[str]
    status: str
    result: Dict[str, Any] | None = Field(sa_column=Column(JSON))
    last_updated: datetime | None