"""
Celery tasks for MarkingAssistant.

This package contains all task definitions organized by functionality.
"""

# Import task modules to ensure they are registered
from . import hello

__all__ = ['hello'] 