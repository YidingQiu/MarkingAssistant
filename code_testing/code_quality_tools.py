import subprocess
import sys
import io
from contextlib import redirect_stdout, redirect_stderr
from flake8.api import legacy as flake8
from pylint import lint
from black import FileMode, format_file_contents

def run_flake8(file_path):
    """Run flake8 on a specific file using default configuration."""
    try:
        # Capture both stdout and stderr
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            style_guide = flake8.get_style_guide()
            report = style_guide.check_files([file_path])
            
        # Get the output
        output_str = output.getvalue()
        if output_str.strip():
            return output_str.strip()
        return "No style issues found"
    except Exception as e:
        return f"Error running flake8: {str(e)}"

def run_pylint(file_path):
    """Run pylint on a specific file using default configuration."""
    try:
        # Capture pylint output
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            lint.Run([file_path], do_exit=False)
            
        # Get the output
        output_str = output.getvalue()
        if output_str.strip():
            return output_str.strip()
        return "No issues found"
    except Exception as e:
        return f"Error running pylint: {str(e)}"

def run_black(file_path):
    """Run black on a specific file using default configuration."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            src = f.read()
        
        # Try to format the code
        try:
            formatted = format_file_contents(src, fast=False, mode=FileMode())
            if formatted != src:
                # If the formatted code is different, show what would change
                return "Code formatting issues found. Black would make these changes:\n" + \
                       "--- Original\n" + \
                       "+++ Formatted\n" + \
                       "".join(
                           f"{'+' if i == 0 else '-'} {line}\n"
                           for i, line in enumerate([src, formatted])
                       )
            return "No formatting issues found"
        except Exception as e:
            return f"Code contains syntax errors: {str(e)}"
    except Exception as e:
        return f"Error running black: {str(e)}"
