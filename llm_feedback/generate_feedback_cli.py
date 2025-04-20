#!/usr/bin/env python3

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional
from .feedback_generator import generate_feedback, FeedbackFormat

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG to see all log messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
        logging.FileHandler('feedback_generation.log')  # Also log to file
    ]
)
logger = logging.getLogger(__name__)

class SmartFormatter(argparse.HelpFormatter):
    """Formatter that handles special characters in usage examples."""
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate feedback for student submissions using LLM.',
        formatter_class=SmartFormatter
    )
    
    parser.add_argument(
        'results_json',
        type=str,
        help='R|Path to the test results JSON file.\n'
             'For filenames with spaces or special characters, use quotes:\n'
             '  "path/to/file with spaces.json"\n'
             '  "path/to/(file with parentheses).json"'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='qwq',
        help='Name of the LLM model to use (default: qwq)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='feedback',
        help='Directory to store generated feedback (default: feedback)'
    )
    
    parser.add_argument(
        '--format',
        type=str,
        choices=['html', 'markdown', 'text'],
        default='markdown',
        help='Format of the generated feedback (default: markdown)'
    )
    
    args = parser.parse_args()
    
    # Handle path normalization
    args.results_json = str(Path(args.results_json).resolve())
    args.output_dir = str(Path(args.output_dir).resolve())
    
    return args

def validate_inputs(results_path: str, output_dir: str) -> Optional[str]:
    """Validate input parameters.
    
    Args:
        results_path: Path to results JSON file
        output_dir: Path to output directory
        
    Returns:
        Error message if validation fails, None otherwise
    """
    # Check if results file exists
    if not Path(results_path).is_file():
        return f"Results file not found: {results_path}"
    
    # Check if results file is JSON
    if not results_path.lower().endswith('.json'):
        return f"Results file must be JSON: {results_path}"
    
    # Try to create output directory if it doesn't exist
    try:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"Failed to create output directory {output_dir}: {str(e)}"
    
    return None

def main() -> int:
    """Main entry point for the feedback generation CLI.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        args = parse_args()
    except Exception as e:
        logger.error(f"Error parsing arguments: {str(e)}")
        logger.error("For filenames with spaces or special characters, use quotes:")
        logger.error('  python -m llm_feedback "path/to/file with spaces.json"')
        logger.error('  python -m llm_feedback "path/to/(file with parentheses).json"')
        return 1
    
    # Validate inputs
    error = validate_inputs(args.results_json, args.output_dir)
    if error:
        logger.error(error)
        return 1
    
    try:
        # Generate feedback
        logger.info(f"Generating feedback using model: {args.model}")
        logger.info(f"Reading results from: {args.results_json}")
        logger.info(f"Output directory: {args.output_dir}")
        logger.info(f"Feedback format: {args.format}")
        
        generate_feedback(
            results_json_path=args.results_json,
            feedback_dir=args.output_dir,
            model_name=args.model,
            feedback_format=args.format
        )
        
        logger.info("Feedback generation completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Error generating feedback: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 