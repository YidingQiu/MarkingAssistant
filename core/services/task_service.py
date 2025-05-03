from typing import List, Optional
from sqlmodel import Session, select

from core.configs import storage
from core.models.task import Task

def create_task(db: Session, task_data: dict) -> Task:
    task = Task(**task_data)
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