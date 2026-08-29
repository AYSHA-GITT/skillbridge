import pdfplumber
from docx import Document
import os


def extract_text_from_pdf(file_path):
    """Extract raw text from a PDF file using pdfplumber."""
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip()


def extract_text_from_docx(file_path):
    """Extract raw text from a DOCX file using python-docx."""
    doc = Document(file_path)
    paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
    return "\n".join(paragraphs).strip()


def parse_resume(file_path):
    """
    Detects file type by extension and extracts text accordingly.
    Returns the extracted plain text, or raises a ValueError if the
    file type isn't supported or the file has no extractable text.
    """
    extension = file_path.rsplit('.', 1)[1].lower()

    if extension == 'pdf':
        text = extract_text_from_pdf(file_path)
    elif extension == 'docx':
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")

    if not text:
        raise ValueError("No extractable text found in this file. "
                          "It may be a scanned/image-based document.")

    return text