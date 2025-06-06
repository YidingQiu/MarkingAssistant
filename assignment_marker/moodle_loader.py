import os
from typing import List, Dict, Tuple, Optional

def get_user_list_for_task(base_submissions_dir: str, task_name: str) -> List[Dict[str, str]]:
    """
    Identifies users who have submissions for a specific task.

    Assumes a structure like: base_submissions_dir / task_name / user_submission_folder
    Example: submissions / Lab1 / z1234567_submission_Student_Name...

    Args:
        base_submissions_dir: The root directory containing all task submissions.
        task_name: The name of the task (e.g., "Lab1", "Ass2").

    Returns:
        A list of dictionaries, each representing a user with 'id' and 'name'.
        Returns an empty list if the task folder doesn't exist or no user folders are found.
    """
    users = []
    task_folder_path = os.path.join(base_submissions_dir, task_name)

    if not os.path.isdir(task_folder_path):
        print(f"Warning: Task folder not found: {task_folder_path}")
        return users # Return empty list if task folder doesn't exist

    # Iterate through items in the specific task folder
    for user_submission_folder in os.listdir(task_folder_path):
        full_path = os.path.join(task_folder_path, user_submission_folder)
        
        # Check if it's a directory and seems like a submission folder
        if os.path.isdir(full_path) and 'submission' in user_submission_folder.lower():
            user_id, user_name = parse_user_folder_name(user_submission_folder)
            if user_id and user_name:
                users.append({
                    'id': user_id,
                    'name': user_name,
                    # Store the full path for easier access later
                    'submission_folder_path': full_path 
                })
                
    return users

def parse_user_folder_name(folder_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parses the user ID and name from a Moodle-style submission folder name.

    Expected format examples: 
    - z1234567_Student Name_assignsubmission_file_
    - z1234567_submission_Student Name__assignsubmission_file

    Args:
        folder_name: The name of the user's submission folder.

    Returns:
        A tuple containing (user_id, user_name) or (None, None) if parsing fails.
    """
    # Handle potential variations in separators more robustly
    parts = folder_name.split('_assignsubmission_file', 1)[0] # Get the part before Moodle suffix
    
    # Try common separators like '_submission_' or just '_' after id
    if '_submission_' in parts:
        id_part, name_part = parts.split('_submission_', 1)
    elif '_' in parts:
        id_part = parts.split('_', 1)[0]
        # Check if the first part looks like a student ID (e.g., starts with 'z' and has digits)
        if id_part.startswith('z') and id_part[1:].isdigit():
             name_part = parts.split('_', 1)[1] if '_' in parts else None
        else:
            id_part, name_part = None, None # Does not match expected ID format
    else:
         id_part, name_part = None, None # Cannot split meaningfully

    # Basic validation
    user_id = id_part if id_part and id_part.startswith('z') else None 
    user_name = name_part.replace('_', ' ') if name_part else None # Replace underscores in names

    if not user_id or not user_name:
        print(f"Warning: Could not parse user ID/name from folder: {folder_name}")
        return None, None

    return user_id, user_name