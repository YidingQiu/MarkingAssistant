import os
import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from code_testing.test_runner_main import run_tests_for_student
from llm_feedback.feedback_generator import generate_feedback, FeedbackFormat
from llm_feedback.report_generator import generate_report
from assignment_marker.moodle_loader import get_user_list_for_task
from assignment_marker.folder_structure_parser import read_submission_files
from assignment_marker.student_code_extractor import (
    extract_code_from_files, 
    extract_markdown_from_ipynb, 
    extract_text_from_document
)
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
        description='Run the marking pipeline for student submissions based on tasks.',
        formatter_class=SmartFormatter
    )
    
    parser.add_argument(
        '--task-name',
        type=str,
        required=True,
        help="""R|Name of the task to process (e.g., Lab1, Ass2).
This corresponds to a key in the config file and a folder in the submissions directory."""
    )
    
    parser.add_argument(
        '--submissions-dir',
        type=str,
        default='submissions',
        help="""R|Path to the base submissions directory.
Expected structure: submissions_dir / task_name / user_submission_folder
For paths with spaces or special characters, use quotes:
  --submissions-dir "path/to/submissions folder" """  # Ensure exactly three closing quotes
    )
    
    parser.add_argument(
        '--config-file',
        type=str,
        default='rubric/marking_config.yaml', # Default assumes config is in rubric dir
        help='Path to the main YAML configuration file defining tasks and their settings.'
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
        '--test-timeout',
        type=int,
        default=30,  # Default timeout of 30 seconds
        help='Maximum time in seconds allowed for running tests for a single problem/task (default: 30)'
    )

    parser.add_argument(
        '--exclude',
        nargs='+',
        choices=['black', 'flake8'],
        default=[],
        help='Exclude specific code quality tools from LLM feedback (choices: black, flake8)'
    )
    
    parser.add_argument(
        '--install-packages',
        action='store_true',
        default=True,
        help='Install required packages from student code (default: True)'
    )
    
    parser.add_argument(
        '--output-target',
        type=str,
        choices=['student_feedback', 'marker_report'],
        default='student_feedback',
        help='Specify whether to generate feedback for students or a report for markers (default: student_feedback)'
    )
    
    args = parser.parse_args()
    
    # Handle path normalization
    args.submissions_dir = str(Path(args.submissions_dir).resolve())
    args.log_file = str(Path(args.log_file).resolve())
    args.config_file = str(Path(args.config_file).resolve()) # Normalize config file path
    
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

def setup_directories(task_name: str) -> Dict[str, Path]:
    """Setup required directories for the marking pipeline based on the task."""
    base_dir = Path.cwd()
    
    # Define directory structure relative to the task
    # Assume config file is in 'rubric' parent dir, adjust if needed
    config_base_dir = base_dir / 'rubric' 
    
    dirs = {
        # Keep submissions separate, actual user folders are inside task subfolder
        'submissions_base': base_dir / 'submissions', 
        'config_base': config_base_dir,
        # Task-specific directories
        'test_cases': config_base_dir / 'test_cases' / task_name,
        'test_results': config_base_dir / 'test_results' / task_name,
        'feedback': base_dir / 'feedback' / task_name
    }
    
    # Create task-specific directories if they don't exist
    for key, dir_path in dirs.items():
        if key not in ['submissions_base', 'config_base']: # Don't create base dirs here
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {dir_path}: {e}")
                # Decide if this is a critical failure or can be handled later
    
    return dirs

def validate_inputs(args: argparse.Namespace) -> Optional[str]:
    """Validate input parameters."""
    # Validate task name (basic check, could add regex)
    if not args.task_name or not args.task_name.strip():
        return "Task name cannot be empty."
    
    # Validate base submissions directory existence
    if not Path(args.submissions_dir).is_dir():
        return f"Base submissions directory not found: {args.submissions_dir}"
        
    # Validate task-specific submissions directory existence (optional check, depends on workflow)
    task_submission_path = Path(args.submissions_dir) / args.task_name
    if not task_submission_path.is_dir():
         logger.warning(f"Task-specific submission directory not found: {task_submission_path}. Proceeding, but no users might be found.")
         # Depending on strictness, could return an error here:
         # return f"Task-specific submission directory not found: {task_submission_path}"
         
    # Validate config file existence
    if not Path(args.config_file).is_file():
        return f"Configuration file not found: {args.config_file}"
    
    # Validate log file directory writability (already handled in setup_logging, but can double-check)
    try:
        Path(args.log_file).parent.mkdir(parents=True, exist_ok=True)
        # Try opening the log file in append mode to check permissions
        with open(args.log_file, 'a'): 
            pass 
    except Exception as e:
        return f"Failed to access or create log file directory for {args.log_file}: {str(e)}"
    
    return None

def process_task(args: argparse.Namespace) -> None:
    """Process all submissions for a specific task."""
    task_name = args.task_name
    
    # Setup directories based on task name
    dirs = setup_directories(task_name)
    
    # Initialize repository with the main config file
    config_repo = RubricRepository(args.config_file)
    
    # Get the specific configuration for this task
    task_config = config_repo.get_task_config(task_name)
    if not task_config:
        logger.error(f"Configuration for task '{task_name}' not found in {args.config_file}")
        return
    logger.info(f"Loaded configuration for task: {task_name}")
    # Example: Access config details like task_config.get('description', 'No description')

    # Get list of users who submitted for this task
    # Pass the base submissions directory and the task name
    users = get_user_list_for_task(args.submissions_dir, task_name)
    if not users:
        logger.warning(f"No user submissions found for task '{task_name}' in {Path(args.submissions_dir) / task_name}")
        return # Nothing to process for this task
    
    logger.info(f"Found {len(users)} user submissions for task '{task_name}'")
    
    # Process each user's submission for the task
    for user_info in users:
        user_id = user_info['id']
        user_name = user_info['name']
        user_submission_folder = user_info.get('submission_folder_path') # Get the full path added earlier

        if not user_submission_folder or not Path(user_submission_folder).is_dir():
             logger.error(f"Submission folder path missing or invalid for user {user_name} ({user_id}). Skipping.")
             continue

        logger.info(f"Processing user: {user_name} ({user_id}) for task: {task_name}")
        
        try:
            # Submission files are within the user's specific folder
            submission_files_paths = read_submission_files(user_submission_folder)
            if not submission_files_paths:
                logger.warning(f"No processable files (.py, .ipynb) found in submission folder for user {user_name}. Skipping.")
                continue
            
            # Extract code, markdown, and text from all relevant files
            student_code_dict: Dict[str, str] = {}
            all_markdown_content: List[str] = []
            all_document_text: Dict[str, str] = {}

            code_file_paths_for_extraction = [] # For extract_code_from_files
            for file_path_str in submission_files_paths:
                if file_path_str.endswith('.ipynb'):
                    code_file_paths_for_extraction.append(file_path_str)
                    all_markdown_content.extend(extract_markdown_from_ipynb(file_path_str))
                elif file_path_str.endswith('.py'):
                    code_file_paths_for_extraction.append(file_path_str)
                elif file_path_str.endswith(('.pdf', '.docx', '.doc', '.txt')):
                    text = extract_text_from_document(file_path_str)
                    if text:
                        all_document_text[Path(file_path_str).name] = text
            
            if code_file_paths_for_extraction:
                student_code_dict = extract_code_from_files(code_file_paths_for_extraction)
            
            if not student_code_dict and not all_markdown_content and not all_document_text:
                logger.error(f"Could not extract any content (code, markdown, or text) for {user_name}. Files: {submission_files_paths}")
                continue
                
            # --- Test Running ---
            test_results_data = None
            if not args.skip_tests:
                logger.info(f"Running tests for {user_name} ({user_id}) on task {task_name}")
                
                # Construct paths for test runner
                # Assuming run_tests_for_student needs user info, the user's specific submission *folder*,
                # the base directory for test cases, and the base directory for results.
                # **Crucially, update run_tests_for_student signature and logic if necessary**
                try:
                    test_results_data = run_tests_for_student(
                        student_info={'id': user_id, 'name': user_name}, # Pass necessary user identifiers
                        submission_folder=user_submission_folder,        # Path to the specific user's files for this task
                        test_cases_dir=str(dirs['test_cases']),          # Task-specific test cases
                        results_dir=str(dirs['test_results']),           # Task-specific results directory
                        task_name=task_name,                             # Pass task name for context/naming
                        test_timeout=args.test_timeout,                  # Pass timeout
                        install_packages=args.install_packages           # Pass install_packages flag
                    )
                    logger.info(f"Tests completed for {user_name} ({user_id})")
                except Exception as test_err:
                    logger.error(f"Error running tests for {user_name} ({user_id}): {test_err}")
                    logger.exception("Detailed test runner error traceback:")
                    # Continue to feedback if possible, or skip user
                    continue 
            else:
                logger.info(f"Skipping tests for {user_name} ({user_id}) as requested.")

            # Define paths for results and quality files, accessible by both feedback and report generation
            results_filename = f"{user_name.replace(' ', '_')}_{user_id}_{task_name}_submission.json"
            results_file_path = dirs['test_results'] / results_filename
            quality_flake8_path = dirs['test_results'].parent / 'flake8_result' / task_name / results_filename.replace('_submission.json', '_flake8_results.json')
            quality_black_path = dirs['test_results'].parent / 'black_result' / task_name / results_filename.replace('_submission.json', '_black_results.json')

            # --- Feedback Generation / Report Generation ---
            if args.output_target == 'student_feedback':
                if not args.skip_feedback:
                    if results_file_path.exists():
                        logger.info(f"Generating student feedback for {user_name} ({user_id}) based on {results_filename}")
                        try:
                            generate_feedback(
                                results_json_path=str(results_file_path) if results_file_path.exists() else None,
                                flake8_json_path=str(quality_flake8_path) if quality_flake8_path.exists() else None,
                                black_json_path=str(quality_black_path) if quality_black_path.exists() else None,
                                task_name=task_name,
                                feedback_dir=str(dirs['feedback']),
                                model_name=args.model,
                                feedback_format=args.feedback_format,
                                exclude_tools=args.exclude,
                                source_code_dict=student_code_dict,
                                markdown_content=all_markdown_content,
                                document_text=all_document_text
                            )
                            logger.info(f"Student feedback generated successfully for {user_name} ({user_id})")
                        except Exception as feedback_err:
                            logger.error(f"Error generating student feedback for {user_name} ({user_id}): {feedback_err}")
                            logger.exception("Detailed student feedback generator error traceback:")
                            # Continue to next user
                    elif args.skip_tests:
                        logger.warning(f"Skipping student feedback for {user_name} ({user_id}): Tests were skipped, no results file expected at {results_file_path}.")
                    else:
                        logger.error(f"Test results file not found for {user_name} ({user_id}). Cannot generate student feedback.")
                        logger.error(f"Expected file: {results_file_path}")
                else:
                    logger.info(f"Skipping student feedback generation for {user_name} ({user_id}) as requested.")
            
            elif args.output_target == 'marker_report':
                if not args.skip_feedback: # Re-using skip_feedback to mean skip_llm_processing for now
                    if results_file_path.exists():
                        logger.info(f"Generating marker report for {user_name} ({user_id}) based on {results_filename}")
                        try:
                            generate_report(
                                results_json_path=str(results_file_path) if results_file_path.exists() else None,
                                flake8_json_path=str(quality_flake8_path) if quality_flake8_path.exists() else None,
                                black_json_path=str(quality_black_path) if quality_black_path.exists() else None,
                                task_name=task_name,
                                report_dir=str(dirs['feedback'].parent / f"{task_name}_marker_reports"),
                                model_name=args.model,
                                source_code_dict=student_code_dict,
                                markdown_content=all_markdown_content,
                                document_text=all_document_text
                            )
                            logger.info(f"Marker report generated successfully for {user_name} ({user_id})")
                        except Exception as report_err:
                            logger.error(f"Error generating marker report for {user_name} ({user_id}): {report_err}")
                            logger.exception("Detailed marker report generator error traceback:")
                    elif args.skip_tests:
                        logger.warning(f"Skipping marker report for {user_name} ({user_id}): Tests were skipped, no results file.")
                    else:
                        logger.error(f"Test results file not found for {user_name} ({user_id}). Cannot generate marker report.")
                else:
                    logger.info(f"Skipping marker report generation for {user_name} ({user_id}) as requested.")

            logger.info(f"Successfully finished processing for user: {user_name} ({user_id}) on task {task_name}")

        except Exception as e:
            logger.error(f"Unhandled error processing user {user_name} ({user_id}) for task {task_name}: {str(e)}")
            logger.exception("Detailed error traceback:")
            # Continue processing next student

def main() -> int:
    """Main entry point for the marking pipeline."""
    args: Optional[argparse.Namespace] = None
    try:
        args = parse_args()
    except Exception as e:
        # Use basic logging if setup failed or hasn't happened yet
        logging.error(f"Error parsing arguments: {str(e)}") 
        return 1
    
    # Setup logging using parsed arguments
    # Do this early so subsequent messages are logged correctly
    setup_logging(args.log_level, args.log_file)
    
    # Validate inputs after logging is configured
    error = validate_inputs(args)
    if error:
        logger.error(f"Input validation failed: {error}")
        return 1
    
    # Log the start of processing with validated args
    logger.info("Starting marking pipeline with arguments:")
    for arg, value in vars(args).items():
        logger.info(f"  {arg}: {value}")

    try:
        # Process the specified task
        process_task(args)
        logger.info(f"Pipeline completed processing for task: {args.task_name}")
        return 0
        
    except Exception as e:
        logger.critical(f"Pipeline failed during processing of task {args.task_name}: {str(e)}")
        logger.exception("Detailed pipeline error traceback:")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 