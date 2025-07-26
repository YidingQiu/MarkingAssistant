"""
Celery worker configuration and utilities.

This package contains worker startup scripts and configuration.
"""

from .startup import setup_worker_environment

__all__ = ['setup_worker_environment'] 