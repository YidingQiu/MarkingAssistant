def get_student_list(submission_folder):
    import os
    
    students = []
    for student_folder in os.listdir(submission_folder):
        if os.path.isdir(os.path.join(submission_folder, student_folder)):
            student_id, name = parse_student_folder(student_folder)
            students.append({'id': student_id, 'name': name})
    return students

def parse_student_folder(folder_name):
    # Format: z1234567_submission_Student Name__assignsubmission_file
    parts = folder_name.split('_submission_')
    
    # Extract student ID (z number)
    student_id = parts[0]  # This will be z1234567
    
    # Extract student name from the second part
    name_part = parts[1].split('__assignsubmission_file')[0]  # This will be "Student Name"
    
    return student_id, name_part