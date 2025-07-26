from celery import Task
from celery.utils.log import get_task_logger
import time
from typing import Any, Dict

logger = get_task_logger(__name__)

class BaseTask(Task):
    """Base task class with common functionality."""
    
    def on_success(self, retval: Any, task_id: str, args: tuple, kwargs: dict) -> None:
        """Called when task succeeds."""
        logger.info(f"Task {task_id} succeeded with result: {retval}")
    
    def on_failure(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo) -> None:
        """Called when task fails."""
        logger.error(f"Task {task_id} failed with exception: {exc}")
    
    def on_retry(self, exc: Exception, task_id: str, args: tuple, kwargs: dict, einfo) -> None:
        """Called when task is retried."""
        logger.warning(f"Task {task_id} retrying due to: {exc}")

class ProgressTask(BaseTask):
    """Task class with progress tracking capability."""
    
    def update_progress(self, current: int, total: int, message: str = "") -> None:
        """Update task progress."""
        percentage = int((current / total) * 100) if total > 0 else 0
        self.update_state(
            state='PROGRESS',
            meta={
                'current': current,
                'total': total,
                'percentage': percentage,
                'message': message
            }
        )
        logger.info(f"Progress: {percentage}% - {message}") 