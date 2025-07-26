import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def setup_worker_environment():
    """Setup environment for Celery worker."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Set environment variables if not already set
    if not os.getenv('PYTHONPATH'):
        os.environ['PYTHONPATH'] = str(project_root)
    
    # Import and setup Django-style settings if needed
    try:
        from core.configs.settings import settings
        logging.info("Settings loaded successfully")
    except ImportError as e:
        logging.error(f"Failed to load settings: {e}")
        sys.exit(1)
    
    logging.info("Worker environment setup complete")

if __name__ == "__main__":
    setup_worker_environment() 