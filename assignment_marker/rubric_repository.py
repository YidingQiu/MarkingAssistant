import yaml
import os

class RubricRepository:
    def __init__(self, rubric_file):
        self.rubric_file = rubric_file
        self.rubrics = self.load_rubrics()

    def load_rubrics(self):
        """Load rubrics from the YAML file."""
        if not os.path.exists(self.rubric_file):
            raise FileNotFoundError(f"Rubric file not found: {self.rubric_file}")
        
        with open(self.rubric_file, 'r') as file:
            return yaml.safe_load(file)

    def get_rubric(self, rubric_name):
        """Get a specific rubric by name."""
        return self.rubrics.get(rubric_name, None)

    def list_rubrics(self):
        """List all available rubrics."""
        return list(self.rubrics.keys())

# Example usage
if __name__ == "__main__":
    rubric_repo = RubricRepository('rubric/marking_rubric.yaml')
    print(rubric_repo.list_rubrics())
