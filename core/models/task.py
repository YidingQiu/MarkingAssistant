from typing import Optional, Dict, Any

from sqlalchemy import Column
from sqlmodel import SQLModel, Field, JSON, Relationship

from core.models.rubric_config import RubricConfig


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str | None
    course_id: int = Field(foreign_key="course.id")
    test_files_url: str | None
    rubric_config_id: int | None = Field(foreign_key="rubric_config.id")
    scoring_config: Dict[str, Any] = Field(sa_column=Column(JSON))

    rubric_config: RubricConfig | None = Relationship()