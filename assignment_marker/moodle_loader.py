def get_student_list(submission_folder):
    import os
    
    students = []
    # First get the lab submission folder
    for lab_folder in os.listdir(submission_folder):
        lab_folder_path = os.path.join(submission_folder, lab_folder)
        if os.path.isdir(lab_folder_path):
            # Then get individual student submissions within the lab folder
            for student_folder in os.listdir(lab_folder_path):
                student_folder_path = os.path.join(lab_folder_path, student_folder)
                if os.path.isdir(student_folder_path) and 'submission' in student_folder:
                    student_id, name = parse_student_folder(student_folder)
                    students.append({
                        'id': student_id,
                        'name': name,
                        'lab_folder': lab_folder
                    })
    return students

def parse_student_folder(folder_name):
    # Format: z1234567_submission_Student Name__assignsubmission_file
    if '_submission_' not in folder_name:
        return None, None
        
    parts = folder_name.split('_submission_')
    
    # Extract student ID (z number)
    student_id = parts[0]  # This will be z1234567
    
    # Extract student name from the second part
    name_part = parts[1].split('__assignsubmission_file')[0]  # This will be "Student Name"
    
    return student_id, name_part