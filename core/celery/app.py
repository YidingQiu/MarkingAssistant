from celery import Celery
from core.configs.celery_settings import CelerySettings
from core.configs.settings import settings

def create_celery_app() -> Celery:
    """Create and configure Celery application."""
    
    celery_app = Celery(
        "marking_assistant",
        broker=CelerySettings.broker_url,
        backend=CelerySettings.result_backend,
        include=[
            'core.celery.tasks.hello',
            # Future task modules will be added here
        ]
    )
    
    # Configure Celery
    celery_app.config_from_object(CelerySettings, namespace='CELERY')
    
    # Task discovery
    celery_app.autodiscover_tasks([
        'core.celery.tasks',
    ])
    
    return celery_app

# Create the Celery app instance
celery_app = create_celery_app()

# For debugging - optional
if __name__ == '__main__':
    celery_app.start() 