def read_submission_files(student_folder):
    import os
    
    submission_files = []
    for root, dirs, files in os.walk(student_folder):
        for file in files:
            if file.endswith('.py') or file.endswith('.ipynb'):  # Adjust based on expected file types
                submission_files.append(os.path.join(root, file))
    return submission_files
