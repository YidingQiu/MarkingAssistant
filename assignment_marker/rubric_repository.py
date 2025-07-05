import yaml
import os
from typing import Dict, Any, List, Optional

class RubricRepository:
    def __init__(self, config_file: str):
        """Initialize repository with the path to the main configuration file."""
        self.config_file = config_file
        self.configs = self._load_configs()

    def _load_configs(self) -> Dict[str, Any]:
        """Load task configurations from the YAML file."""
        if not os.path.exists(self.config_file):
            # Consider logging this error instead of raising immediately
            # Or handle the absence of a file more gracefully depending on requirements
            print(f"Error: Configuration file not found: {self.config_file}")
            return {} # Return empty dict if file not found
        
        try:
            with open(self.config_file, 'r') as file:
                # Expecting a top-level dictionary where keys are task names (e.g., "Lab1")
                loaded_data = yaml.safe_load(file)
                if not isinstance(loaded_data, dict):
                    print(f"Error: Configuration file {self.config_file} should contain a top-level dictionary.")
                    return {}
                return loaded_data
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file {self.config_file}: {e}")
            return {}
        except Exception as e:
            print(f"Error reading configuration file {self.config_file}: {e}")
            return {}

    def get_task_config(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get the configuration for a specific task by its name."""
        return self.configs.get(task_name, None)

    def list_tasks(self) -> List[str]:
        """List all tasks defined in the configuration file."""
        return list(self.configs.keys())

# Example of expected YAML structure in 'marking_config.yaml':
# Lab1:
#   description: "Introduction to Python"
#   total_marks: 10
#   scoring_config:
#     pass_fail: True
#   test_files_pattern: "test_lab1_*.py"
# Ass2:
#   description: "Data Structures Assignment"
#   total_marks: 50
#   scoring_config:
#      deductions_per_failure: 5
#   test_files_pattern: "test_ass2_*.py"


# Example usage (assuming a 'marking_config.yaml' exists)
# if __name__ == "__main__":
#     repo = RubricRepository('rubric/marking_config.yaml')
#     print("Available tasks:", repo.list_tasks())
#     lab1_config = repo.get_task_config('Lab1')
#     if lab1_config:
#         print("\nLab1 Config:", lab1_config)
#     else:
#         print("\nLab1 config not found.")
