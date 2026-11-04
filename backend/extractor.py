import os
import re
import io
from PIL import Image

# Import PyMuPDF and PyMuPDF4LLM for high-accuracy document parsing
try:
    import pymupdf as fitz
except ImportError:
    import fitz

try:
    import pymupdf4llm
    HAS_PYMUPDF4LLM = True
except ImportError:
    HAS_PYMUPDF4LLM = False

from docx import Document

# Optional Tesseract or RapidOCR
try:
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False

try:
    from rapidocr_onnxruntime import RapidOCR
    rapid_ocr = RapidOCR()
    HAS_RAPID_OCR = True
except Exception:
    HAS_RAPID_OCR = False

def clean_extracted_text(text: str) -> str:
    """
    Cleans raw text by removing null bytes, fixing hyphenated word-breaks across lines,
    and normalizing whitespace while preserving readable structure.
    """
    if not text:
        return ""
    # Remove null characters
    text = text.replace('\x00', ' ')
    # Fix hyphenated words at line-breaks (e.g. "instruc-\ntion" -> "instruction")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Normalize excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_text_from_pdf(file_path: str):
    """
    Extracts text page by page with high accuracy.
    Uses PyMuPDF4LLM (Markdown structuring) with RapidOCR/Tesseract fallback for scanned documents.
    """
    pages_data = []

    # First attempt: Try PyMuPDF4LLM for rich structured text (tables, headings, lists)
    if HAS_PYMUPDF4LLM:
        try:
            chunks = pymupdf4llm.to_markdown(file_path, page_chunks=True)
            for idx, c in enumerate(chunks):
                raw_text = c.get("text", "")
                cleaned = clean_extracted_text(raw_text)
                
                # Check if page is empty or image-based
                if len(cleaned) < 25 and HAS_RAPID_OCR:
                    try:
                        doc = fitz.open(file_path)
                        pix = doc[idx].get_pixmap()
                        img_bytes = pix.tobytes("png")
                        ocr_result, _ = rapid_ocr(img_bytes)
                        if ocr_result:
                            ocr_lines = [line[1] for line in ocr_result if line[1]]
                            cleaned = f"[Scanned Page - OCR Extracted]\n" + "\n".join(ocr_lines)
                        doc.close()
                    except Exception:
                        pass

                pages_data.append({
                    "page": idx + 1,
                    "text": cleaned if cleaned else "[No text or image content detected on this page]"
                })
            if pages_data:
                return pages_data
        except Exception as e:
            print(f"PyMuPDF4LLM parsing failed: {e}. Falling back to standard PyMuPDF.")

    # Fallback attempt: Standard PyMuPDF
    doc = fitz.open(file_path)
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = clean_extracted_text(page.get_text("text"))

        # OCR fallback if page has negligible text
        if len(text) < 25:
            pix = page.get_pixmap()
            img_bytes = pix.tobytes("png")
            if HAS_RAPID_OCR:
                try:
                    ocr_result, _ = rapid_ocr(img_bytes)
                    if ocr_result:
                        ocr_lines = [line[1] for line in ocr_result if line[1]]
                        text = f"[Scanned Page - OCR Extracted]\n" + "\n".join(ocr_lines)
                except Exception:
                    pass
            elif OCR_AVAILABLE:
                try:
                    img = Image.open(io.BytesIO(img_bytes))
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if ocr_text:
                        text = f"[OCR Extracted]\n{ocr_text}"
                except Exception:
                    pass

        pages_data.append({
            "page": page_num + 1,
            "text": text if text else "[Empty or image-only page]"
        })

    doc.close()
    return pages_data

def extract_text_from_docx(file_path: str):
    """
    Extracts text from DOCX files and groups paragraphs & tables into readable page chunks.
    """
    doc = Document(file_path)
    full_paragraphs = []
    
    for para in doc.paragraphs:
        t = clean_extracted_text(para.text)
        if t:
            full_paragraphs.append(t)
            
    for table in doc.tables:
        for row in table.rows:
            row_text = [clean_extracted_text(cell.text) for cell in row.cells if cell.text.strip()]
            if row_text:
                full_paragraphs.append(" | ".join(row_text))

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
        cleaned_line = clean_extracted_text(line)
        if not cleaned_line:
            continue
        words = len(cleaned_line.split())
        current_page.append(cleaned_line)
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
