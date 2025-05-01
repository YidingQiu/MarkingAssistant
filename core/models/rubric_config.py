from enum import Enum
from typing import Optional, Dict, Any
from sqlmodel import SQLModel, Field, JSON

class RubricScope(str, Enum):
    public = "public"
    private = "private"

class RubricConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    value: Dict[str, Any] = Field(sa_column=JSON)
    scope: RubricScope = Field(default=RubricScope.public)