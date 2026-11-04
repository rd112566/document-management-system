import os
try:
    import pymupdf as fitz
except ImportError:
    import fitz
from docx import Document
from PIL import Image
import io

# Optional pytesseract for OCR fallback
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

def extract_text_from_pdf(file_path: str):
    """
    Extracts text page by page using PyMuPDF.
    If a page contains no text (e.g., scanned image), it tries Tesseract OCR as fallback.
    """
    doc = fitz.open(file_path)
    pages_data = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text().strip()

        # Fallback to OCR if page has negligible text
        if len(text) < 20 and OCR_AVAILABLE:
            try:
                pix = page.get_pixmap()
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                ocr_text = pytesseract.image_to_string(img).strip()
                if ocr_text:
                    text = f"[OCR Extracted]\n{ocr_text}"
            except Exception:
                pass  # Fallback to whatever text was found or empty

        pages_data.append({
            "page": page_num + 1,
            "text": text if text else "[Empty or image-only page]"
        })

    doc.close()
    return pages_data

def extract_text_from_docx(file_path: str):
    """
    Extracts text from DOCX files and groups paragraphs into readable page chunks.
    """
    doc = Document(file_path)
    full_paragraphs = []
    
    for para in doc.paragraphs:
        t = para.text.strip()
        if t:
            full_paragraphs.append(t)
            
    for table in doc.tables:
        for row in table.rows:
            row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_text:
                full_paragraphs.append(" | ".join(row_text))

    # Approximate ~300 words per page
    pages_data = []
    current_page = []
    current_words = 0
    page_num = 1

    for p in full_paragraphs:
        words = len(p.split())
        current_page.append(p)
        current_words += words
        if current_words >= 350:
            pages_data.append({
                "page": page_num,
                "text": "\n\n".join(current_page)
            })
            page_num += 1
            current_page = []
            current_words = 0

    if current_page or not pages_data:
        pages_data.append({
            "page": page_num,
            "text": "\n\n".join(current_page) if current_page else "[Empty Document]"
        })

    return pages_data

def extract_text_from_txt(file_path: str):
    """
    Extracts text from plain text files, chunking into pages of ~400 words.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    lines = content.splitlines()
    pages_data = []
    current_page = []
    current_words = 0
    page_num = 1

    for line in lines:
        words = len(line.split())
        current_page.append(line)
        current_words += words
        if current_words >= 400:
            pages_data.append({
                "page": page_num,
                "text": "\n".join(current_page)
            })
            page_num += 1
            current_page = []
            current_words = 0

    if current_page or not pages_data:
        pages_data.append({
            "page": page_num,
            "text": "\n".join(current_page) if current_page else "[Empty Document]"
        })

    return pages_data

def extract_document_text(file_path: str, file_type: str):
    """
    Dispatcher function based on extension.
    Returns: list of {"page": int, "text": str}
    """
    ext = file_type.lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ["docx", "doc"]:
        return extract_text_from_docx(file_path)
    elif ext == "txt":
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")
