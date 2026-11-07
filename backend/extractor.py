import os
import re
import io
import csv
import json
from PIL import Image

# High-performance PyMuPDF
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    import openpyxl
except ImportError:
    openpyxl = None

# Optional OCR fallback for scanned/image-only PDFs
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
    Cleans raw text by removing null bytes, fixing private-use font characters (bullets),
    and de-hyphenating words across line-breaks.
    """
    if not text:
        return ""
    # Replace null bytes
    text = text.replace('\x00', ' ')
    # Replace private use area characters (common in PDFs for bullet points)
    text = re.sub(r'[\ue000-\uf8ff]', '• ', text)
    # Fix hyphenated words at line-breaks (e.g. "instruc-\ntion" -> "instruction")
    text = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Normalize excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_text_from_pdf(file_path: str):
    """
    High-speed, memory-efficient PDF text extraction using PyMuPDF.
    Extracts pages with page numbering and falls back to OCR only for scanned/image-only pages.
    """
    if fitz is None:
        raise ImportError("PyMuPDF (fitz) is not installed.")

    pages_data = []
    doc = fitz.open(file_path)

    for page_num in range(len(doc)):
        page = doc[page_num]
        raw_text = page.get_text("text")
        cleaned = clean_extracted_text(raw_text)

        # Fallback to OCR ONLY if page is truly image-based or blank (< 25 characters)
        if len(cleaned) < 25:
            try:
                pix = page.get_pixmap(dpi=150)
                img_bytes = pix.tobytes("png")

                if HAS_RAPID_OCR:
                    ocr_result, _ = rapid_ocr(img_bytes)
                    if ocr_result:
                        ocr_lines = [line[1] for line in ocr_result if line[1]]
                        cleaned = "[Scanned Page - OCR]\n" + "\n".join(ocr_lines)
                elif OCR_AVAILABLE:
                    img = Image.open(io.BytesIO(img_bytes))
                    ocr_text = pytesseract.image_to_string(img).strip()
                    if ocr_text:
                        cleaned = f"[OCR Extracted]\n{ocr_text}"
            except Exception:
                pass

        pages_data.append({
            "page": page_num + 1,
            "text": cleaned if cleaned else "[No readable text content detected on this page]"
        })

    doc.close()
    return pages_data

def extract_text_from_docx(file_path: str):
    """
    Extracts text from DOCX files and groups paragraphs & tables into readable page chunks.
    """
    if Document is None:
        raise ImportError("python-docx is not installed.")

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
    Extracts text from plain text or markdown files, chunking into logical pages of ~350 words.
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
        if current_words >= 350:
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

def extract_text_from_csv(file_path: str):
    """
    Extracts structured rows from CSV/TSV files and groups them into logical pages.
    """
    pages_data = []
    rows_text = []
    
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        # Detect delimiter
        sample = f.read(2048)
        f.seek(0)
        delimiter = "\t" if "\t" in sample and sample.count("\t") > sample.count(",") else ","
        reader = csv.reader(f, delimiter=delimiter)
        
        headers = []
        try:
            headers = next(reader)
        except StopIteration:
            headers = []

        headers = [h.strip() for h in headers if h.strip()]

        for row_idx, row in enumerate(reader, start=1):
            if not row:
                continue
            if headers:
                row_items = [f"{headers[i]}: {row[i].strip()}" for i in range(min(len(headers), len(row))) if row[i].strip()]
                row_str = " | ".join(row_items)
            else:
                row_str = " | ".join(c.strip() for c in row if c.strip())
            
            if row_str:
                rows_text.append(f"Row {row_idx}: {row_str}")

    page_size = 25
    page_num = 1
    for i in range(0, len(rows_text), page_size):
        chunk = rows_text[i:i + page_size]
        pages_data.append({
            "page": page_num,
            "text": "\n".join(chunk)
        })
        page_num += 1

    if not pages_data:
        pages_data.append({"page": 1, "text": "[Empty CSV Table]"})

    return pages_data

def extract_text_from_excel(file_path: str):
    """
    Extracts structured sheets and rows from Excel files (.xlsx).
    """
    if openpyxl is None:
        raise ImportError("openpyxl is not installed.")

    wb = openpyxl.load_workbook(file_path, data_only=True)
    pages_data = []
    page_num = 1

    for sheet_name in wb.sheetnames:
        sheet = wb[sheet_name]
        sheet_rows = []
        headers = []

        for row_idx, row in enumerate(sheet.iter_rows(values_only=True), start=1):
            values = [str(v).strip() for v in row if v is not None and str(v).strip()]
            if not values:
                continue
            if not headers:
                headers = values
                continue

            row_items = []
            for col_idx, val in enumerate(values):
                col_name = headers[col_idx] if col_idx < len(headers) else f"Col{col_idx+1}"
                row_items.append(f"{col_name}: {val}")
            
            sheet_rows.append(f"Row {row_idx}: " + " | ".join(row_items))

        page_size = 30
        for i in range(0, max(1, len(sheet_rows)), page_size):
            chunk = sheet_rows[i:i + page_size]
            text = f"Sheet: {sheet_name}\n" + ("\n".join(chunk) if chunk else "[Empty Sheet]")
            pages_data.append({
                "page": page_num,
                "text": text
            })
            page_num += 1

    wb.close()
    return pages_data if pages_data else [{"page": 1, "text": "[Empty Spreadsheet]"}]

def extract_text_from_json(file_path: str):
    """
    Extracts and pretty-formats JSON data into readable logical page chunks.
    """
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        data = json.load(f)

    pretty_str = json.dumps(data, indent=2)
    lines = pretty_str.splitlines()
    
    pages_data = []
    page_size = 50
    page_num = 1
    for i in range(0, len(lines), page_size):
        chunk = lines[i:i + page_size]
        pages_data.append({
            "page": page_num,
            "text": "\n".join(chunk)
        })
        page_num += 1

    return pages_data if pages_data else [{"page": 1, "text": "[Empty JSON Document]"}]

def extract_document_text(file_path: str, file_type: str):
    """
    Dispatcher function based on extension.
    Supported types: PDF, DOCX, DOC, TXT, MD, CSV, TSV, XLSX, XLS, JSON.
    Returns: list of {"page": int, "text": str}
    """
    ext = file_type.lower()
    if ext == "pdf":
        return extract_text_from_pdf(file_path)
    elif ext in ["docx", "doc"]:
        return extract_text_from_docx(file_path)
    elif ext in ["txt", "md", "markdown"]:
        return extract_text_from_txt(file_path)
    elif ext in ["csv", "tsv"]:
        return extract_text_from_csv(file_path)
    elif ext in ["xlsx", "xls"]:
        return extract_text_from_excel(file_path)
    elif ext == "json":
        return extract_text_from_json(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}. Supported formats: PDF, DOCX, TXT, MD, CSV, XLSX, JSON")
