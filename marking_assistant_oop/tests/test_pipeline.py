import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import os

import sys
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from marking_assistant.pipelines.marking_pipeline import MarkingPipeline
from marking_assistant.assignments.student import Student
from marking_assistant.assignments.submission import Submission

class TestMarkingPipeline(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        # Mock config that defines a modular pipeline
        self.mock_config = {
            "task_name": "TestModularTask",
            "submissions_dir": str(self.test_dir / "submissions"),
            "results_dir": str(self.test_dir / "results"),
            "feedback_dir": str(self.test_dir / "feedback"),
            "test_cases_dir": str(self.test_dir / "test_cases"),
            "model": "llama3.1:latest",
            "modules": [
                {
                    "module_id": "overview",
                    "system_prompt_template": "Summarize.",
                    "user_prompt_template": "Data: {all_code}",
                    "required_data": {"all_code": "all_code"}
                },
                {
                    "module_id": "polishing",
                    "system_prompt_template": "Polish this text.",
                    "user_prompt_template": "{overview_output}",
                    "required_data": {"overview_output": "module_output:overview"}
                }
            ],
            "report_structure": {
                "header": "Report for {user_name}",
                "footer": "End of Report",
                "sections": [
                    {"module_id": "overview", "title": "## Overview"},
                    {"module_id": "polishing", "title": "## Final Comments"}
                ]
            }
        }
    
    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('marking_assistant.pipelines.marking_pipeline.MoodleLoader')
    @patch('marking_assistant.pipelines.marking_pipeline.TestRunner')
    @patch('marking_assistant.pipelines.marking_pipeline.LLMProvider')
    @patch('pathlib.Path.write_text')
    def test_pipeline_orchestration(self, mock_write_text, MockLLMProvider, MockTestRunner, MockMoodleLoader):
        # --- Setup Mocks ---
        # Mock loader to return one submission
        mock_student = Student(id="z123", name="Test Student")
        mock_submission = Submission(mock_student, "dummy_path")
        mock_submission.files = [Path("dummy_path/problem1.py")]
        MockMoodleLoader.return_value.get_submissions_for_task.return_value = [mock_submission]

        # Mock runner to return some results
        MockTestRunner.return_value.run_tests_for_submission.return_value = ({}, {})

        # Mock LLM provider to return different content for each module
        mock_llm_instance = MockLLMProvider.return_value
        mock_llm_instance.generate.side_effect = [
            MagicMock(success=True, content="This is the overview."),
            MagicMock(success=True, content="This is the polished text.")
        ]
        
        # --- Run Pipeline ---
        pipeline = MarkingPipeline(self.mock_config)
        pipeline.run()

        # --- Assertions ---
        # Check that the final report was written
        mock_write_text.assert_called_once()
        
        # Check the content of the final report
        final_report_content = mock_write_text.call_args[0][0]
        self.assertIn("Report for Test Student", final_report_content)
        self.assertIn("## Overview\nThis is the overview.", final_report_content)
        self.assertIn("## Final Comments\nThis is the polished text.", final_report_content)
        self.assertIn("End of Report", final_report_content)

        # Check that the LLM was called twice (once for each module)
        self.assertEqual(mock_llm_instance.generate.call_count, 2)

if __name__ == '__main__':
    unittest.main() 