import os
from pathlib import Path
from typing import List, Optional
import logging
import zipfile # Added for zip file handling

logger = logging.getLogger(__name__)

def read_submission_files(submission_dir: str) -> List[str]:
    """
    Reads relevant submission files (.py, .ipynb) from a directory.
    If .zip files are found, they are extracted, and then their contents are scanned.
    The original .zip file is deleted after successful extraction.
    """
    submission_path = Path(submission_dir)
    processed_files: List[str] = []

    if not submission_path.is_dir():
        logger.error(f"Submission directory not found: {submission_dir}")
        return processed_files

    # First, handle any zip files by extracting them
    # Using rglob to find zip files in any subdirectory as well
    zip_files = list(submission_path.rglob('*.zip'))
    for zip_file_path in zip_files:
        try:
            logger.info(f"Found zip file: {zip_file_path}. Attempting to extract...")
            # Extract to the same directory where the zip file is located
            extract_to_path = zip_file_path.parent 
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to_path)
            logger.info(f"Successfully extracted {zip_file_path} to {extract_to_path}")
            
            # After successful extraction, delete the zip file
            try:
                os.remove(zip_file_path)
                logger.info(f"Successfully deleted zip file: {zip_file_path}")
            except OSError as e:
                logger.error(f"Error deleting zip file {zip_file_path} after extraction: {e}")
        except zipfile.BadZipFile:
            logger.error(f"Error: {zip_file_path} is a bad zip file. Skipping.")
        except Exception as e:
            logger.error(f"Error extracting {zip_file_path}: {e}")

    # Now, glob for .py and .ipynb files (including any newly extracted ones)
    for ext in ('*.py', '*.ipynb'):
        for file_path in submission_path.rglob(ext):
            # Ensure we are not picking up files from unwanted directories like __MACOSX or .ipynb_checkpoints
            # Also, skip the .zip files themselves if they weren't deleted for some reason
            if ("__MACOSX" in str(file_path) or \
               ".ipynb_checkpoints" in str(file_path) or \
               file_path.suffix == '.zip'):
                continue
            if file_path.is_file():
                processed_files.append(str(file_path.resolve()))
    
    if not processed_files:
        logger.warning(f"No .py or .ipynb files found in {submission_dir} after processing zips.")
    else:
        logger.info(f"Found processable files: {processed_files} in {submission_dir}")
        
    return processed_files

# Placeholder for other potential functions in this file
def parse_folder_structure(base_dir: str) -> dict[str, list[str]]:
    # This is a simplified example, your actual parsing might be more complex
    # and align with how get_user_list_for_task works.
    structure = {}
    # ... logic to parse ...
    return structure
