from kombu import Queue
import os

class CeleryConfig:
    """Base Celery configuration."""
    
    # Broker settings
    broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
    result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
    
    # Basic settings
    task_serializer = 'json'
    accept_content = ['json']
    result_serializer = 'json'
    timezone = 'UTC'
    enable_utc = True
    
    # Worker settings
    worker_prefetch_multiplier = 1
    worker_max_tasks_per_child = 100
    worker_disable_rate_limits = False
    worker_log_format = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
    worker_task_log_format = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'
    
    # Task settings
    task_track_started = True
    task_time_limit = 30 * 60  # 30 minutes
    task_soft_time_limit = 25 * 60  # 25 minutes
    task_default_retry_delay = 60
    task_max_retries = 3
    
    # Queue configuration
    task_default_queue = 'default'
    task_queues = (
        Queue('default', routing_key='default'),
        Queue('marking', routing_key='marking'),
        Queue('llm', routing_key='llm'),
        Queue('testing', routing_key='testing'),
        Queue('reports', routing_key='reports'),
    )
    
    # Task routing (for future use)
    task_routes = {
        'core.celery.tasks.hello.*': {'queue': 'default'},
        # Future routing rules will be added here
    }
    
    # Result settings
    result_expires = 3600  # 1 hour
    result_persistent = True
    
    # Monitoring
    worker_send_task_events = True
    task_send_sent_event = True 