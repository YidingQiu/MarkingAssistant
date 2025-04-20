import os
import json
from typing import Dict

def extract_code_from_files(file_paths: list) -> Dict[str, str]:
    """Extract code from Python files and Jupyter notebooks."""
    code_dict = {}
    
    for file_path in file_paths:
        try:
            if file_path.endswith('.ipynb'):
                # Handle Jupyter notebook
                with open(file_path, 'r', encoding='utf-8') as f:
                    notebook = json.load(f)
                
                # Extract code from all code cells
                code_cells = []
                for cell in notebook['cells']:
                    if cell['cell_type'] == 'code':
                        code_cells.extend(cell['source'])
                
                code_dict[file_path] = ''.join(code_cells)
            else:
                # Handle Python file
                with open(file_path, 'r', encoding='utf-8') as f:
                    code_dict[file_path] = f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {str(e)}")
            continue
    
    return code_dict
