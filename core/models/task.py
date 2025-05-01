from typing import Optional, Dict, Any

from sqlalchemy import Column
from sqlmodel import SQLModel, Field, JSON

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str
    rubric_config: Dict[str, Any] = Field(sa_column=Column(JSON))
    scoring_config: Dict[str, Any] = Field(sa_column=Column(JSON))
    test_files_path: str