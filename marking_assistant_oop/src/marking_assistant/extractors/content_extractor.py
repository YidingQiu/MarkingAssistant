import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union

# Attempt to import PDF and DOCX libraries, log if not available
try:
    import PyPDF2
except ImportError:
    PyPDF2 = None
    logging.warning("PyPDF2 not installed. PDF text extraction will be skipped.")

try:
    from docx import Document as DocxDocument
except ImportError:
    DocxDocument = None
    logging.warning("python-docx not installed. DOCX text extraction will be skipped.")

logger = logging.getLogger(__name__)


class ContentExtractor:
    """A utility class to extract content from various file types."""

    @staticmethod
    def _load_notebook_json(path: Path) -> Optional[Dict]:
        """Loads a Jupyter notebook and returns it as a dictionary with robust error handling."""
        try:
            content = path.read_text(encoding='utf-8', errors='ignore')
            notebook_json = json.loads(content)
            
            # Handle cases where the notebook is a JSON-encoded string inside the file
            if isinstance(notebook_json, str):
                logger.debug(f"Notebook content for {path} was a string, attempting to parse again.")
                notebook_json = json.loads(notebook_json)

            if not isinstance(notebook_json, dict):
                logger.error(f"Failed to parse notebook, expected a JSON object but got {type(notebook_json).__name__} for {path}")
                return None
            return notebook_json
        except json.JSONDecodeError as e:
            # Handle common notebook corruption issue where there's extra data after the JSON object
            if "Extra data" in str(e):
                try:
                    logger.warning(f"Attempting to fix invalid JSON in {path} by removing trailing characters.")
                    fixed_content = content[:e.pos]
                    notebook_json = json.loads(fixed_content)
                    if isinstance(notebook_json, dict):
                        logger.info(f"Successfully fixed and parsed JSON for {path}")
                        return notebook_json
                except json.JSONDecodeError:
                    logger.error(f"Failed to fix and re-parse JSON for {path}. Original error: {e}")
                    return None # Fall through to return None
            
            logger.error(f"Invalid JSON in notebook file {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error reading notebook file {path}: {e}")
            return None

    @staticmethod
    def extract_code(file_path: Union[str, Path]) -> Optional[str]:
        """Extracts code content from a Python or Jupyter Notebook file."""
        path = Path(file_path)
        try:
            if path.suffix == '.py':
                return path.read_text(encoding='utf-8')
            elif path.suffix == '.ipynb':
                notebook_json = ContentExtractor._load_notebook_json(path)
                if not notebook_json:
                    return None
                
                cells = notebook_json.get('cells', [])
                if not isinstance(cells, list):
                    logger.warning(f"'cells' key in notebook {path.name} is not a list.")
                    return None

                code_cells = [
                    "".join(cell.get('source', []))
                    for cell in cells
                    if isinstance(cell, dict) and cell.get('cell_type') == 'code'
                ]
                return "\n\n# In[ ]:\n".join(code_cells)
        except Exception as e:
            logger.error(f"Error reading or parsing code from {path}: {e}")
        return None

    @staticmethod
    def extract_text(file_path: Union[str, Path]) -> Optional[str]:
        """Extracts text content from PDF, DOCX, or TXT files."""
        path = Path(file_path)
        logger.debug(f"Attempting to extract text from document: {path}")

        try:
            if path.suffix == '.pdf':
                return ContentExtractor._extract_from_pdf(path)
            elif path.suffix == '.docx':
                return ContentExtractor._extract_from_docx(path)
            elif path.suffix == '.txt':
                return path.read_text(encoding='utf-8')
        except Exception as e:
            logger.error(f"Error extracting text from {path}: {e}", exc_info=True)
        
        logger.debug(f"File type not supported for text extraction or library missing: {path.suffix}")
        return None

    @staticmethod
    def _extract_from_pdf(path: Path) -> Optional[str]:
        if not PyPDF2:
            logger.warning(f"PyPDF2 not available, skipping PDF: {path}")
            return None
        
        text_content = ""
        with path.open('rb') as f:
            reader = PyPDF2.PdfReader(f)
            if reader.is_encrypted:
                try:
                    reader.decrypt('')
                except Exception as decrypt_err:
                    logger.warning(f"Could not decrypt PDF {path}: {decrypt_err}.")
            
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content += page_text + "\n"
        
        logger.info(f"Successfully extracted text from PDF: {path}" if text_content else f"No text extracted from PDF: {path}")
        return text_content.strip() if text_content.strip() else None

    @staticmethod
    def _extract_from_docx(path: Path) -> Optional[str]:
        if not DocxDocument:
            logger.warning(f"python-docx not available, skipping DOCX: {path}")
            return None
            
        doc = DocxDocument(path)
        text_content = "\n".join([para.text for para in doc.paragraphs])
        logger.info(f"Successfully extracted text from DOCX: {path}" if text_content else f"No text extracted from DOCX: {path}")
        return text_content.strip() if text_content.strip() else None

    @staticmethod
    def extract_markdown(file_path: Union[str, Path]) -> List[str]:
        """Extracts all markdown cell content from a Jupyter Notebook file."""
        path = Path(file_path)
        markdown_cells = []
        if path.suffix != '.ipynb':
            return markdown_cells

        try:
            notebook_json = ContentExtractor._load_notebook_json(path)
            if not notebook_json:
                return markdown_cells

            cells = notebook_json.get('cells', [])
            if not isinstance(cells, list):
                logger.warning(f"'cells' key in notebook {path.name} is not a list.")
                return markdown_cells
                
            markdown_cells = [
                "".join(cell.get('source', []))
                for cell in cells
                if isinstance(cell, dict) and cell.get('cell_type') == 'markdown'
            ]
            logger.info(f"Extracted {len(markdown_cells)} markdown cells from {path}")
        except Exception as e:
            logger.error(f"Error extracting markdown from ipynb {path}: {e}", exc_info=True)
        return markdown_cells 