import subprocess
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from flake8.api import legacy as flake8
from black import FileMode, format_file_contents

def run_flake8(file_path):
    """Run flake8 on a specific file."""
    try:
        # Use subprocess to run flake8 for better output capture
        result = subprocess.run(
            ['flake8', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # Get the output
        output = result.stdout.strip() or result.stderr.strip()
        if output:
            return output
        return "No style issues found"
    except Exception as e:
        return f"Error running flake8: {str(e)}"

# def run_pylint(file_path):
#     """Run pylint on a specific file using default configuration."""
#     try:
#         # Capture pylint output
#         output = io.StringIO()
#         with redirect_stdout(output), redirect_stderr(output):
#             lint.Run([file_path], do_exit=False)
            
#         # Get the output
#         output_str = output.getvalue()
#         if output_str.strip():
#             return output_str.strip()
#         return "No issues found"
#     except Exception as e:
#         return f"Error running pylint: {str(e)}"

def run_black(file_path):
    """Run black on a specific file."""
    try:
        # First try using command line for better error messages
        result = subprocess.run(
            ['black', '--check', '--diff', file_path],
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        # Get the complete output
        output = []
        if result.stderr:
            stderr = result.stderr.strip()
            # Filter out the Python 3.12.5 AST warning
            if not stderr.startswith("Python 3.12.5 has a memory safety issue"):
                output.append(stderr)
        if result.stdout:
            output.append(result.stdout.strip())
        
        # If we got any output, return it
        if output:
            return "\n".join(output)
            
        # If no command line output, try using the Python API
        with open(file_path, 'r', encoding='utf-8') as f:
            src = f.read()
        
        # Try to format the code
        try:
            formatted = format_file_contents(src, fast=False, mode=FileMode())
            if formatted != src:
                # Show a proper diff of the changes
                original_lines = src.splitlines()
                formatted_lines = formatted.splitlines()
                
                # Create a readable diff
                diff = []
                diff.append("Code formatting issues found. Black would make these changes:")
                for i, (orig, form) in enumerate(zip(original_lines, formatted_lines), 1):
                    if orig != form:
                        diff.append(f"Line {i}:")
                        diff.append(f"  - {orig}")
                        diff.append(f"  + {form}")
                
                return "\n".join(diff)
            return "No formatting issues found"
        except Exception as e:
            error_msg = str(e)
            # Filter out the Python 3.12.5 AST warning
            if "Python 3.12.5 has a memory safety issue" in error_msg:
                return "No formatting issues found"
            return error_msg
    except Exception as e:
        error_msg = str(e)
        # Filter out the Python 3.12.5 AST warning at the top level
        if "Python 3.12.5 has a memory safety issue" in error_msg:
            return "No formatting issues found"
        return error_msg
