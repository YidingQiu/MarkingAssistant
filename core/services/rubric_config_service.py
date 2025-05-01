from typing import List, Optional

from sqlmodel import Session, select

from core.models.rubric_config import RubricConfig, RubricScope


def get_by_id(rubric_config_id: int, db: Session) -> Optional[RubricConfig]:
    return db.get(RubricConfig, rubric_config_id)


def list_by_scope(scope: RubricScope, db: Session) -> List[RubricConfig]:
    statement = select(RubricConfig).where(RubricConfig.scope == scope)
    return db.exec(statement).all()


def create(db: Session, value: dict, scope: RubricScope = RubricScope.public) -> RubricConfig:
    rubric_config = RubricConfig(value=value, scope=scope)
    db.add(rubric_config)
    db.commit()
    db.refresh(rubric_config)
    return rubric_config
