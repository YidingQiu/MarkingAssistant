import os
from pathlib import Path
from typing import List, Dict, Optional
import logging
import json

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

def extract_code_from_files(file_paths: List[str]) -> Dict[str, str]:
    """Extracts code content from a list of Python or Jupyter Notebook files."""
    extracted_code = {}
    for file_path in file_paths:
        path = Path(file_path)
        try:
            if path.suffix == '.py':
                with open(path, 'r', encoding='utf-8') as f:
                    extracted_code[file_path] = f.read()
            elif path.suffix == '.ipynb':
                with open(path, 'r', encoding='utf-8') as f:
                    notebook_json = json.load(f)
                code_cells = []
                for cell in notebook_json.get('cells', []):
                    if cell.get('cell_type') == 'code':
                        code_cells.append("".join(cell.get('source', [])))
                extracted_code[file_path] = "\n\n# In[ ]:\n".join(code_cells) # Basic concatenation
            # else: (student_text_extractor will handle other types)
        except Exception as e:
            logger.error(f"Error reading or parsing code from {file_path}: {e}")
    return extracted_code

def extract_text_from_document(file_path_str: str) -> Optional[str]:
    """Extracts text content from PDF or DOCX files."""
    file_path = Path(file_path_str)
    logger.debug(f"Attempting to extract text from document: {file_path}")
    if file_path.suffix == '.pdf':
        if not PyPDF2:
            logger.warning(f"PyPDF2 not available, skipping PDF text extraction for {file_path}")
            return None
        try:
            text = ""
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                if reader.is_encrypted:
                    try:
                        reader.decrypt('') # Try with empty password
                    except Exception as decrypt_err:
                        logger.warning(f"Could not decrypt PDF {file_path}: {decrypt_err}. Text extraction might fail or be incomplete.")
                
                for page_num in range(len(reader.pages)):
                    page = reader.pages[page_num]
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Successfully extracted text from PDF: {file_path}" if text else f"No text extracted from PDF: {file_path}")
            return text if text.strip() else None
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}", exc_info=True)
            return None
    elif file_path.suffix == '.docx':
        if not DocxDocument:
            logger.warning(f"python-docx not available, skipping DOCX text extraction for {file_path}")
            return None
        try:
            doc = DocxDocument(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
            logger.info(f"Successfully extracted text from DOCX: {file_path}" if text else f"No text extracted from DOCX: {file_path}")
            return text if text.strip() else None
        except Exception as e:
            logger.error(f"Error extracting text from DOCX {file_path}: {e}", exc_info=True)
            return None
    # Add .doc handling here if needed (e.g., using textract or antiword via subprocess)
    # For .txt files, just read them directly.
    elif file_path.suffix == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()
            logger.info(f"Successfully read text from TXT: {file_path}")
            return text
        except Exception as e:
            logger.error(f"Error reading text from TXT {file_path}: {e}", exc_info=True)
            return None
    logger.debug(f"File type not supported for text extraction or library missing: {file_path.suffix}")
    return None

def extract_markdown_from_ipynb(file_path_str: str) -> List[str]:
    """Extracts all markdown cell content from a Jupyter Notebook file."""
    markdown_cells = []
    try:
        with open(file_path_str, 'r', encoding='utf-8') as f:
            notebook_json = json.load(f)
        for cell in notebook_json.get('cells', []):
            if cell.get('cell_type') == 'markdown':
                markdown_cells.append("".join(cell.get('source', [])))
        logger.info(f"Extracted {len(markdown_cells)} markdown cells from {file_path_str}")
    except Exception as e:
        logger.error(f"Error extracting markdown from ipynb {file_path_str}: {e}", exc_info=True)
    return markdown_cells
