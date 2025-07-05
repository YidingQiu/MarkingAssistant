from typing import List
from .submission import Submission

class Assignment:
    """Represents a collection of submissions for a single task."""

    def __init__(self, task_name: str, submissions: List[Submission]):
        self.task_name = task_name
        self.submissions = submissions

    @property
    def student_count(self) -> int:
        """Returns the number of student submissions for this assignment."""
        return len(self.submissions)

    def __repr__(self) -> str:
        return f"Assignment(task='{self.task_name}', submissions={self.student_count})" 