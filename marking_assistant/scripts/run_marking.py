import argparse
import logging
from pathlib import Path
import sys

# Add the src directory to the Python path to allow for absolute imports
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from marking_assistant.config.repository import ConfigRepository
from marking_assistant.pipelines.marking_pipeline import MarkingPipeline

# Logger will be configured in main based on command-line arguments
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Run the new OOP marking pipeline.')
    
    parser.add_argument(
        '--task-name', type=str, required=True, help="Name of the task to process."
    )
    parser.add_argument(
        '--config-dir', type=str, default='rubric/tasks',
        help='Path to the directory containing task configuration files.'
    )
    parser.add_argument(
        '--submissions-dir', type=str, default="submissions",
        help="Directory containing student submissions."
    )
    parser.add_argument(
        '--results-dir', type=str, default="results",
        help="Directory where test results should be saved."
    )
    parser.add_argument(
        '--feedback-dir', type=str, default="feedback",
        help="Directory where final feedback reports should be saved."
    )
    parser.add_argument(
        '--model', type=str, default="openai-gpt-4o",
        help="Name of the LLM model to use for feedback generation."
    )
    parser.add_argument(
        '--temperature', type=float, default=0.1,
        help='Temperature for LLM generation (e.g., 0.2 for more deterministic, 0.7 for more creative).'
    )
    parser.add_argument(
        '--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO', help='Set the logging level for console and file output.'
    )
    parser.add_argument(
        '--log-file', type=str, default='marking_pipeline_oop.log',
        help='Path to the log file.'
    )
    parser.add_argument(
        '--skip-tests', action='store_true',
        help='Skip running tests and only generate feedback (requires existing test results).'
    )
    parser.add_argument(
        '--no-save-intermediate', action='store_true',
        help='If set, intermediate LLM prompts and responses for each module will not be saved.'
    )
    
    return parser.parse_args()


def main():
    """Main entry point for the OOP marking pipeline."""
    args = parse_args()

    # Configure logging based on command-line arguments.
    # Using force=True to ensure reconfiguration works even if logging was touched before.
    logging.basicConfig(
        level=args.log_level.upper(),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(args.log_file, mode='w') # Overwrite log file each run
        ],
        force=True
    )

    logger.info(f"Loading task configurations from: {args.config_dir}")
    config_repo = ConfigRepository(args.config_dir)
    
    task_config = config_repo.get_task_config(args.task_name)
    if not task_config:
        logger.error(f"Task '{args.task_name}' not found in {args.config_dir}. Exiting.")
        return

    # Augment YAML config with CLI args. CLI args take precedence.
    cli_args_dict = vars(args)
    # Convert the negative CLI flag to a positive config option for the pipeline
    cli_args_dict['save_intermediate_responses'] = not cli_args_dict.pop('no_save_intermediate', False)
    task_config.update(cli_args_dict)
    
    logger.info(f"Initializing marking pipeline for task: {args.task_name}")
    pipeline = MarkingPipeline(config=task_config)
    pipeline.run()


if __name__ == '__main__':
    main() 