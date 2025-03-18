def extract_code_from_files(file_paths):
    code_snippets = {}
    for file_path in file_paths:
        with open(file_path, 'r') as file:
            code_snippets[file_path] = file.read()
    return code_snippets
