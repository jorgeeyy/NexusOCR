import logging

import pytesseract
from django.conf import settings
from PIL import Image

from .preprocessing import preprocess_image
from .postprocessing import clean_text

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def extract_text_from_image(image: Image.Image) -> str:
    processed = preprocess_image(image)
    hocr = pytesseract.image_to_pdf_or_hocr(processed, extension='hocr').decode('utf-8')
    return clean_text(hocr)


def extract_high_fidelity_pdf(file_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(file_path)
        html_out = []
        for page in doc:
            html_out.append(page.get_text("html"))
        doc.close()
        return clean_text("\n".join(html_out))
    except Exception as e:
        logger.error(f"High-fidelity PDF extraction failed: {e}")
        return ""


def extract_scanned_pdf(file_path: str) -> str:
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, dpi=300, poppler_path=settings.POPPLER_PATH)
        page_texts = []
        for i, page_image in enumerate(images, start=1):
            text = extract_text_from_image(page_image)
            if text:
                page_texts.append(text)
        return "\n\n".join(page_texts)
    except Exception as e:
        logger.error(f"Scanned PDF extraction failed: {e}")
        raise RuntimeError(f"Failed to convert PDF: {e}")


def process_document(doc) -> str:
    """Process a DocumentData instance and extract text.

    Tries digital extraction first for PDFs, falling back to OCR if needed.
    For images, uses HOCR for better layout preservation.
    """
    from ..storage import TempStorage

    file_path = str(doc.file_path)
    TempStorage.update_status(doc.uuid, 'processing')

    try:
        if doc.is_pdf:
            text = extract_high_fidelity_pdf(file_path)
            if len(text.strip()) < 100:
                logger.info(f"PDF seems scanned, switching to OCR for {doc.filename}")
                text = extract_scanned_pdf(file_path)

        elif doc.is_image:
            image = Image.open(file_path)
            text = extract_text_from_image(image)

        else:
            raise ValueError(f"Unsupported file type: {doc.file_extension}")

        TempStorage.update_status(doc.uuid, 'done')
        return text

    except Exception as e:
        TempStorage.update_status(doc.uuid, 'failed')
        logger.error(f"OCR failed for {doc.filename}: {e}")
        raise
