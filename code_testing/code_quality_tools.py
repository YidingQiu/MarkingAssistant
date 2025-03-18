import subprocess

def run_flake8(directory):
    """Run flake8 on the specified directory."""
    result = subprocess.run(['flake8', directory], capture_output=True, text=True)
    return result.stdout

def run_pylint(file_path):
    """Run pylint on a specific file."""
    result = subprocess.run(['pylint', file_path], capture_output=True, text=True)
    return result.stdout

def run_black(directory):
    """Run black on the specified directory."""
    result = subprocess.run(['black', directory], capture_output=True, text=True)
    return result.stdout
