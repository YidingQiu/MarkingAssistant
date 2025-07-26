from celery import current_task
from core.celery.app import celery_app
from core.celery.tasks.base import BaseTask, ProgressTask
from celery.utils.log import get_task_logger
import time

logger = get_task_logger(__name__)

@celery_app.task(base=BaseTask, bind=True)
def hello_world(self, name: str = "World") -> str:
    """Simple hello world task for testing Celery setup."""
    logger.info(f"Starting hello_world task with name: {name}")
    
    # Simulate some work
    time.sleep(2)
    
    result = f"Hello, {name}! Task ID: {self.request.id}"
    logger.info(f"Completed hello_world task: {result}")
    
    return result

@celery_app.task(base=ProgressTask, bind=True)
def hello_progress(self, name: str = "World", steps: int = 5) -> str:
    """Hello world task with progress tracking."""
    logger.info(f"Starting hello_progress task with {steps} steps")
    
    for i in range(steps):
        # Simulate work
        time.sleep(1)
        
        # Update progress
        self.update_progress(
            current=i + 1,
            total=steps,
            message=f"Processing step {i + 1} of {steps}"
        )
    
    result = f"Hello, {name}! Completed {steps} steps. Task ID: {self.request.id}"
    logger.info(f"Completed hello_progress task: {result}")
    
    return result

@celery_app.task(base=BaseTask, bind=True)
def test_error_handling(self, should_fail: bool = False) -> str:
    """Task for testing error handling and retries."""
    logger.info(f"Starting test_error_handling task, should_fail: {should_fail}")
    
    if should_fail:
        # Test retry mechanism
        if self.request.retries < 2:
            logger.warning(f"Simulating failure, retry {self.request.retries}")
            raise Exception(f"Simulated failure (retry {self.request.retries})")
        else:
            logger.info("Max retries reached, succeeding now")
    
    time.sleep(1)
    result = f"Task completed successfully! Retries: {self.request.retries}"
    
    return result 