import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import fnmatch

from ..assignments.submission import Submission
from ..extractors.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)


class DataCollector:
    """
    Gathers and prepares data from various sources for a specific feedback module.
    """

    def __init__(self, submission: Submission, test_results: Dict, quality_results: Dict):
        self.submission = submission
        self.test_results = test_results
        self.quality_results = quality_results
        
        self._extract_content()

    def _extract_content(self):
        """Pre-extracts all content from submission files."""
        self.source_code: Dict[str, str] = {}
        self.markdown_content: Dict[str, str] = {}
        self.document_text: Dict[str, str] = {}

        logger.debug(f"DataCollector: Processing submission files for student {self.submission.student.id}")
        logger.debug(f"DataCollector: Found files: {[file.name for file in self.submission.files]}")

        for file in self.submission.files:
            logger.debug(f"DataCollector: Attempting to extract content from file: {file.name} ({file})")
            if file.suffix in ['.py', '.ipynb']:
                code = ContentExtractor.extract_code(file)
                if code is not None:
                    self.source_code[file.name] = code
                    logger.debug(f"  -> Extracted code from {file.name}")
                else:
                    if file.suffix == '.ipynb' and file.name not in self.source_code:
                        self.source_code[file.name] = ""
                    logger.debug(f"  -> No code extracted from {file.name}")

            if file.suffix == '.ipynb':
                md = ContentExtractor.extract_markdown(file)
                if md:
                    self.markdown_content[file.name] = "\n\n---\n\n".join(md)
                    logger.debug(f"  -> Extracted markdown from {file.name}")
                else:
                    logger.debug(f"  -> No markdown extracted from {file.name}")

            if file.suffix in ['.pdf', '.docx', '.doc', '.txt']:
                text = ContentExtractor.extract_text(file)
                if text:
                    self.document_text[file.name] = text
                    logger.debug(f"  -> Extracted text from {file.name}")
        
        logger.debug(f"DataCollector: Final source_code keys: {list(self.source_code.keys())}")
        logger.debug(f"DataCollector: Final markdown_content keys: {list(self.markdown_content.keys())}")

    def gather_data_for_module(self, required_data: Dict[str, str], module_outputs: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Gathers data for a module based on the required_data specification.
        
        The specifier format is "data_type:specifier", e.g., "code_file:problem1.py".
        """
        prompt_vars = {}
        if module_outputs is None:
            module_outputs = {}

        for placeholder, specifier in required_data.items():
            try:
                data_type, value_key = specifier.split(':', 1)
                data = self._get_data_by_type(data_type, value_key, module_outputs)
                prompt_vars[placeholder] = data if data is not None else f"[Data not found for specifier: {specifier}]"
            except ValueError:
                # Handle specifiers without a value_key, like 'all_code'
                data = self._get_data_by_type(specifier, None, module_outputs)
                prompt_vars[placeholder] = data if data is not None else f"[Data not found for specifier: {specifier}]"

        return prompt_vars

    def _get_data_by_type(self, data_type: str, key: Optional[str], module_outputs: Dict[str, Any]) -> Any:
        """Retrieves a piece of data based on its type and an optional key, supporting pattern matching."""
        if data_type == 'module_output' and key:
            return module_outputs.get(key)
        
        # Handle data types that support pattern matching
        if data_type in ['code_file', 'markdown_file', 'document_file'] and key and '*' in key:
            source_dict = {
                'code_file': self.source_code,
                'markdown_file': self.markdown_content,
                'document_file': self.document_text
            }.get(data_type, {})
            
            logger.debug(f"DataCollector: Pattern matching for '{key}' in {data_type}. Available files: {list(source_dict.keys())}")

            for filename, content in source_dict.items():
                if fnmatch.fnmatch(filename, key):
                    logger.info(f"Matched pattern '{key}' to file '{filename}' for data type '{data_type}'.")
                    return content
            logger.warning(f"No file found matching pattern '{key}' for data type '{data_type}'.")
            return None

        # Handle exact matches for file-based data
        if data_type == 'code_file' and key:
            return self.source_code.get(key)
        if data_type == 'markdown_file' and key:
            return self.markdown_content.get(key)
        if data_type == 'document_file' and key:
            return self.document_text.get(key)
            
        # Handle non-file data types
        if data_type == 'all_code':
            return "\n\n".join(self.source_code.values())
        if data_type == 'test_group' and key:
            return self.test_results.get('problems', {}).get(key, {})
        if data_type == 'quality_group' and key:
            return self.quality_results.get('problems', {}).get(key, {})
        
        logger.warning(f"Unknown or unsupported data type/key combination: {data_type}:{key}")
        return None 