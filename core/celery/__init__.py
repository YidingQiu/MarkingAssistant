"""
Celery integration for MarkingAssistant.

This package contains the Celery application configuration, task definitions,
and worker setup for asynchronous task processing.
"""

from .app import celery_app

__all__ = ['celery_app'] 