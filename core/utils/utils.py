STORAGE_PRIVATE_BUCKET = 'marking-ai'


def make_solution_file_path(course_id, task_id, user_id, file_name):
    solutions_subdir = user_id or 'bulk'
    return f"courses/{course_id}/tasks/{task_id}/solutions/{solutions_subdir}/{file_name}"
