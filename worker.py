#!/usr/bin/env python3
"""
Celery Worker Entry Point for MarkingAssistant

This module serves as the main entry point for Celery workers on Windows.
It ensures proper Python path setup and module imports.
"""

import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set PYTHONPATH environment variable for spawned processes
os.environ.setdefault('PYTHONPATH', str(project_root))

# Now import the Celery app
from core.celery.app import celery_app

# Make the app available as 'app' for Celery CLI
app = celery_app

if __name__ == '__main__':
    celery_app.start() 