def extract_code_from_files(file_paths):
    code_snippets = {}
    for file_path in file_paths:
        try:
            # Try UTF-8 first, then fallback to other encodings if needed
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    code_snippets[file_path] = file.read()
            except UnicodeDecodeError:
                with open(file_path, 'r', encoding='utf-8-sig') as file:
                    code_snippets[file_path] = file.read()
        except Exception as e:
            print(f"Warning: Could not read file {file_path}: {str(e)}")
            continue
    return code_snippets
