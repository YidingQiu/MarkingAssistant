import os
import argparse
import sys
from pathlib import Path
from typing import Optional
import logging
from code_testing.test_runner_main import run_tests_for_student
from llm_feedback.feedback_generator import generate_feedback, FeedbackFormat
from assignment_marker.moodle_loader import get_student_list, parse_student_folder
from assignment_marker.folder_structure_parser import read_submission_files
from assignment_marker.student_code_extractor import extract_code_from_files
from assignment_marker.rubric_repository import RubricRepository

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
        logging.FileHandler('marking_pipeline.log')  # Also log to file
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
        description='Run the marking pipeline for student submissions.',
        formatter_class=SmartFormatter
    )
    
    parser.add_argument(
        '--group-name',
        type=str,
        required=True,
        help='R|Name of the group to process (e.g., Lab1, Ass2).\n'
             'Must start with either "Lab" or "Ass" followed by a number.'
    )
    
    parser.add_argument(
        '--submissions-dir',
        type=str,
        default='submissions',
        help='R|Path to submissions directory.\n'
             'For paths with spaces or special characters, use quotes:\n'
             '  --submissions-dir "path/to/submissions folder"'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='openai-gpt-o1-mini',
        help='Name of the LLM model to use for feedback generation (default: openai-gpt-o1-mini)'
    )
    
    parser.add_argument(
        '--feedback-format',
        type=str,
        choices=['html', 'markdown', 'text'],
        default='markdown',
        help='Format of the generated feedback (default: markdown)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default='marking_pipeline.log',
        help='Path to log file (default: marking_pipeline.log)'
    )
    
    parser.add_argument(
        '--skip-feedback',
        action='store_true',
        help='Skip feedback generation and only run tests'
    )
    
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip test running and only generate feedback'
    )
    
    parser.add_argument(
        '--rubric-file',
        type=str,
        default='rubric/marking_rubric.yaml',
        help='Path to the rubric YAML file'
    )
    
    parser.add_argument(
        '--test-timeout',
        type=int,
        default=30,  # Default timeout of 30 seconds
        help='Maximum time in seconds allowed for running tests for a single problem (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Handle path normalization
    args.submissions_dir = str(Path(args.submissions_dir).resolve())
    args.log_file = str(Path(args.log_file).resolve())
    args.rubric_file = str(Path(args.rubric_file).resolve())
    
    return args

def setup_logging(log_level: str, log_file: str) -> None:
    """Setup logging configuration."""
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Setup file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set log level
    logger.setLevel(getattr(logging, log_level))

def setup_directories(group_type: str, group_number: str) -> dict:
    """Setup required directories for the marking pipeline."""
    base_dir = Path.cwd()
    group_key = f"{group_type}{group_number}"
    
    # Define directory structure
    dirs = {
        'submissions': base_dir / 'submissions',
        'rubric': base_dir / 'rubric',
        'test_cases': base_dir / 'rubric' / 'test_cases' / group_key,
        'test_results': base_dir / 'rubric' / 'test_results' / group_key,
        'feedback': base_dir / 'feedback' / group_key
    }
    
    # Create directories if they don't exist
    for dir_path in dirs.values():
        dir_path.mkdir(parents=True, exist_ok=True)
    
    return dirs

def validate_inputs(args: argparse.Namespace) -> Optional[str]:
    """Validate input parameters."""
    # Validate group name format
    if not (args.group_name.startswith('Lab') or args.group_name.startswith('Ass')):
        return "Group name must start with 'Lab' or 'Ass'"
    
    # Validate submissions directory
    if not Path(args.submissions_dir).is_dir():
        return f"Submissions directory not found: {args.submissions_dir}"
    
    # Validate rubric file
    if not Path(args.rubric_file).is_file():
        return f"Rubric file not found: {args.rubric_file}"
    
    # Validate log file directory
    log_dir = Path(args.log_file).parent
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"Failed to create log directory {log_dir}: {str(e)}"
    
    return None

def process_group(args: argparse.Namespace) -> None:
    """Process all submissions for a specific group."""
    # Parse group name
    group_type = 'Lab' if args.group_name.startswith('Lab') else 'Ass'
    group_number = args.group_name.replace(group_type, '')
    
    # Setup directories
    dirs = setup_directories(group_type, group_number)
    
    # Initialize rubric repository
    rubric_repo = RubricRepository(args.rubric_file)
    
    # Get list of students
    students = get_student_list(args.submissions_dir)
    if not students:
        logger.error(f"No students found in {args.submissions_dir}")
        return
    
    # Filter students for the specified group
    group_students = [s for s in students if f"{group_type}{group_number}" in s['lab_folder'].replace(' ', '')]
    if not group_students:
        logger.error(f"No students found for {args.group_name}")
        return
    
    logger.info(f"Found {len(group_students)} students for {args.group_name}")
    
    # Process each student
    for student in group_students:
        logger.info(f"Processing student: {student['name']} ({student['id']})")
        
        try:
            # Find student's submission folder
            student_folder = None
            for folder in os.listdir(os.path.join(args.submissions_dir, student['lab_folder'])):
                if student['id'] in folder and student['name'].replace(' ', '') in folder.replace(' ', ''):
                    student_folder = os.path.join(args.submissions_dir, student['lab_folder'], folder)
                    break
            
            if not student_folder:
                logger.error(f"Could not find submission folder for student {student['name']}")
                continue
            
            # Get list of Python files in submission
            submission_files = read_submission_files(student_folder)
            if not submission_files:
                logger.error(f"No Python files found in submission for {student['name']}")
                continue
            
            # Extract code from files
            student_code = extract_code_from_files(submission_files)
            if not student_code:
                logger.error(f"Could not read any files for {student['name']}")
                continue
            
            # Run tests if not skipped
            if not args.skip_tests:
                logger.info(f"Running tests for {student['name']}")
                run_tests_for_student(
                    student_info=student,
                    submission_folder=str(dirs['submissions']),
                    rubric_dir=str(dirs['rubric']),
                    base_results_dir=str(dirs['rubric']),
                    test_timeout=args.test_timeout
                )
            
            # Generate feedback if not skipped
            if not args.skip_feedback:
                # Match the test runner's file naming format
                results_file = dirs['test_results'] / f"{student['name']}_{student['id']}_{args.group_name}_results.json"
                if results_file.exists():
                    logger.info(f"Generating feedback for {student['name']}")
                    generate_feedback(
                        results_json_path=str(results_file),
                        feedback_dir=str(dirs['feedback']),
                        model_name=args.model,
                        feedback_format=args.feedback_format
                    )
                    logger.info(f"Successfully processed {student['name']}")
                else:
                    logger.error(f"Test results file not found for {student['name']}")
                    logger.error(f"Expected file: {results_file}")
                
        except Exception as e:
            logger.error(f"Error processing student {student['name']}: {str(e)}")
            logger.exception("Detailed error traceback:")

def read_submission_files(submission_dir: str) -> list:
    """Read all Python and Jupyter notebook files from a submission directory."""
    files = []
    for root, _, filenames in os.walk(submission_dir):
        for filename in filenames:
            if filename.endswith('.py') or filename.endswith('.ipynb'):
                files.append(os.path.join(root, filename))
    return files

def main() -> int:
    """Main entry point for the marking pipeline."""
    try:
        args = parse_args()
    except Exception as e:
        logger.error(f"Error parsing arguments: {str(e)}")
        return 1
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Validate inputs
    error = validate_inputs(args)
    if error:
        logger.error(error)
        return 1
    
    try:
        # Process the specified group
        process_group(args)
        logger.info("Pipeline completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        logger.exception("Detailed error traceback:")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 