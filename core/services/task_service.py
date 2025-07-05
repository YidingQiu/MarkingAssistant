from typing import List, Optional, Dict, Any
from sqlmodel import Session, select

from core.configs import storage
from core.models.task import Task


def create_task(db: Session, name, description: str|None, course_id: int, test_files_url:str
                , scoring_config: Dict[str, Any], rubric_config_id: int|None) -> Task:
    task = Task(name=name, description=description, course_id=course_id, test_files_url=test_files_url
                , scoring_config=scoring_config, rubric_config_id=rubric_config_id)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def get_task(db: Session, task_id: int, include_test_files: bool = False) -> Optional[Task]:
    task = db.get(Task, task_id)
    if not task:
        return None
    if include_test_files and task.test_files_url:
        # Download and attach test files content (add as a dynamic attribute)
        task.test_files_content = storage.download_file(task.test_files_url)
    return task


def list_tasks_by_course_id(db: Session, course_id: int) -> List[Task]:
    statement = select(Task).where(Task.course_id == course_id)
    return db.exec(statement).all()

# TODO: make safe update
def update_task(db: Session, task_id: int, update_data: dict) -> Optional[Task]:
    task = db.get(Task, task_id)
    if not task:
        return None
    for key, value in update_data.items():
        if hasattr(task, key):
            setattr(task, key, value)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task
