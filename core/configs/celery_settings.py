import os
from core.configs.settings import settings

class CelerySettings:
    """Celery settings that integrate with main application settings."""
    
    # Use Redis from existing infrastructure or default
    broker_url = os.getenv(
        'CELERY_BROKER_URL', 
        f'redis://{getattr(settings, "REDIS_HOST", "localhost")}:{getattr(settings, "REDIS_PORT", "6379")}/0'
    )
    
    result_backend = os.getenv(
        'CELERY_RESULT_BACKEND',
        f'redis://{getattr(settings, "REDIS_HOST", "localhost")}:{getattr(settings, "REDIS_PORT", "6379")}/0'
    )
    
    # Extend with any environment-specific overrides
    if hasattr(settings, 'DEBUG') and settings.DEBUG:
        # Development settings
        worker_log_level = 'DEBUG'
        worker_hijack_root_logger = False
    else:
        # Production settings
        worker_log_level = 'INFO'
        worker_hijack_root_logger = True 