import logging
import subprocess
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CodeQualityRunner:
    """Runs code quality tools like Flake8 and Black on a given file."""

    @staticmethod
    def run_all_checks(file_path: str) -> Dict[str, Any]:
        """Runs all configured quality checks on a single file."""
        results = {
            'flake8': CodeQualityRunner.run_flake8(file_path),
            'black': CodeQualityRunner.run_black(file_path),
        }
        return results

    @staticmethod
    def run_flake8(file_path: str) -> Dict[str, Any]:
        """Runs Flake8 and returns a structured result."""
        try:
            result = subprocess.run(
                ['flake8', file_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            output = result.stdout.strip() or result.stderr.strip()
            has_issues = bool(output)
            
            return {
                'name': 'Flake8',
                'description': 'Style Guide Enforcement',
                'output': output if has_issues else "No style issues found.",
                'has_issues': has_issues
            }
        except FileNotFoundError:
            logger.warning("flake8 command not found. Please ensure it is installed.")
            return {'error': 'flake8 not found.'}
        except Exception as e:
            logger.error(f"Error running flake8 on {file_path}: {e}")
            return {'error': str(e)}

    @staticmethod
    def run_black(file_path: str) -> Dict[str, Any]:
        """Runs Black in check mode and returns a structured result."""
        try:
            result = subprocess.run(
                ['black', '--check', '--diff', file_path],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            # Black exits with 0 if no changes needed, 1 if changes would be made.
            # Stderr may contain info even on success (e.g., "1 file would be reformatted").
            output = result.stderr.strip() or result.stdout.strip()
            has_issues = result.returncode != 0
            
            return {
                'name': 'Black',
                'description': 'Code Formatting',
                'output': output if has_issues else "No formatting issues found.",
                'has_issues': has_issues
            }
        except FileNotFoundError:
            logger.warning("black command not found. Please ensure it is installed.")
            return {'error': 'black not found.'}
        except Exception as e:
            logger.error(f"Error running black on {file_path}: {e}")
            return {'error': str(e)} 