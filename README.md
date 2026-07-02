# NexusOCR

NexusOCR is a fast, clean, and locally-hosted Document Parsing and Optical Character Recognition (OCR) web application built with Django and Tailwind CSS. It extracts text from images and PDFs, preserves formatting (bold, italic, headings, alignment, tables), and provides a WYSIWYG editing workspace with auto-save.

> **Live at [`nexusocr.onrender.com`](https://nexusocr.onrender.com)** — free, no sign-up required.

## Features

- **Dual-Theme UI:** Seamless Light and Premium Dark Mode toggling.
- **Image OCR (Tesseract):** Upload images and extract text via Tesseract OCR with OpenCV preprocessing for accuracy.
- **PDF Text Extraction:** Digital PDFs are parsed via PyMuPDF (fitz) with position-aware layout detection — preserves right-aligned addresses, centered headings, bold/italic text.
- **Scanned PDF Fallback:** If a PDF has no selectable text (<100 chars), it falls back to Tesseract OCR automatically.
- **WYSIWYG Editor:** SunEditor-based rich text editing workspace with formatting toolbar, auto-save (2s debounce), and live word count.
- **Multi-Format Export:** Download as Plain Text (`.txt`), Word Document (`.docx` — layout-preserving via pdf2docx for PDFs), or Spreadsheet (`.xlsx`).
- **Secure File Cleanup:** Automatic cleanup of expired uploads; manual delete with confirmation modal.

---

## Local Development Setup

### 1. Prerequisites (Windows)

- **Python 3.10+**
- **Tesseract-OCR:** Download from [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki). Default path: `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **Poppler:** Download the latest Poppler binary and place it in the project root or add to your System PATH.

### 2. Environment Setup

```bash
git clone <repo>
cd NexusOCR

uv venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # Mac/Linux

uv pip install -r requirements.txt
```

### 3. Configuration

Copy or edit `ocr_project/settings.py` to set:

- `TESSERACT_CMD` — path to the Tesseract executable
- `POPPLER_PATH` — path to the Poppler `bin` directory

### 4. Database & Server

```bash
python manage.py migrate
python manage.py runserver
```

Navigate to `http://localhost:8000`.

---

## Architecture

```
Upload → TempStorage (disk) → process_document()
                                │
                    ┌───────────┴───────────┐
                    │                       │
                  Image                   PDF
                    │                       │
              preprocess.py        extract_pdf_formatted_html()
              (grayscale,           (fitz → position-aware HTML)
               upscale)                │
                    │              pdf2docx → .docx (for export)
              Tesseract OCR             │
                    │              fallback: extract_scanned_pdf()
                    │              (pdf2image → Tesseract OCR)
                    │                       │
                    └───────────┬───────────┘
                                │
                    extracted_text.txt
                                │
                    document_detail.html
                    SunEditor (auto-save → update_document_text)
```

## Tech Stack

- **Backend:** Django 5.x, Python 3.10+
- **OCR:** Tesseract (pytesseract), OpenCV (opencv-python-headless), Pillow
- **PDF:** PyMuPDF (fitz), pdf2image, pdf2docx, python-docx
- **Frontend:** Tailwind CSS, SunEditor (WYSIWYG), Phosphor Icons
- **Sanitization:** bleach, tinycss2

---

## License

MIT
