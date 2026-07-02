import base64
import fitz
import html as html_mod
import io
import logging
import re

import pytesseract
from django.conf import settings
from PIL import Image as PILImage

from ..storage import TempStorage
from .preprocessing import preprocess_image
from .postprocessing import clean_text

logger = logging.getLogger(__name__)

pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD


def extract_text_from_image(image: PILImage.Image) -> str:
    processed = preprocess_image(image)
    text = pytesseract.image_to_string(processed, config='--psm 6 -c preserve_interword_spaces=1')
    return clean_text(text)


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


_BULLET_RE = re.compile(r'^[\s\u00A0]*[•\-\*◦▪➢→‣⁃►▸▹▪▫●○◆◇ ][\s\u00A0]')
_NUMBERED_RE = re.compile(r'^[\s\u00A0]*\d+[\.\)]\s+')
_MARKER_ONLY_RE = re.compile(r'^[\s\u00A0]*([•\-\*◦▪➢→‣⁃►▸▹▪▫●○◆◇ ]|\d+[\.\)])[\s\u00A0]*$')


def _is_marker_only(text: str) -> bool:
    """Check if a line contains only a bullet/number marker."""
    return bool(_MARKER_ONLY_RE.match(text))


def _classify_line(text: str) -> str | None:
    """Classify a line as 'bullet', 'ordered', or None (paragraph).

    Strips any inline HTML tags first so markers inside <strong>, <em>, etc.
    are still detected.
    """
    plain = re.sub(r'<[^>]+>', '', text)
    if _BULLET_RE.match(plain):
        return 'bullet'
    if _NUMBERED_RE.match(plain):
        return 'ordered'
    return None


def _strip_list_marker(text: str) -> str:
    """Remove the bullet/number marker from the start of a line."""
    text = re.sub(r'^[\s\u00A0]*\S+\s+', '', text, count=1)
    text = re.sub(r'^</[a-zA-Z]+>', '', text)
    return text


def _extract_table_html(t):
    """Extract a table as HTML, collapsing grid-line artifacts from PyMuPDF."""
    raw_rows = t.extract()

    # Collapse: filter out None and empty cells that are grid-line artifacts
    def _clean_row(row):
        return [str(c).strip() for c in row if c is not None and str(c).strip()]

    rows = [_clean_row(r) for r in raw_rows if _clean_row(r)]

    if not rows:
        return ""

    # Detect header: use first row as <th> only if all cells are short (< 40 chars)
    # and not the only data row
    use_header = (
        len(rows) > 1
        and all(len(c) < 40 for c in rows[0])
        and any(len(c) >= 40 for r in rows[1:] for c in r)
    )

    html_rows = []
    for idx, row in enumerate(rows):
        tag = "th" if use_header and idx == 0 else "td"
        cells_html = "".join(
            f"<{tag}>{html_mod.escape(c)}</{tag}>" for c in row
        )
        html_rows.append(f"<tr>{cells_html}</tr>")

    return '<table border="1" style="border-collapse:collapse;width:100%">\n' + "\n".join(html_rows) + "\n</table>"


def _image_to_data_uri(page, xref):
    """Extract an embedded image from a PDF page and return (bbox, data_uri).

    Skips images smaller than 100px (icons) and returns None for failures.
    Max output dimension is 800px to keep HTML size manageable.
    """
    try:
        pix = fitz.Pixmap(page.parent, xref)
        if pix.n > 4 or (pix.n == 4 and not pix.alpha):
            pix = fitz.Pixmap(fitz.csRGB, pix)

        # Convert to PNG bytes
        img_bytes = pix.tobytes("png")
        pil_img = PILImage.open(io.BytesIO(img_bytes))

        max_dim = 800
        if pil_img.width > max_dim or pil_img.height > max_dim:
            scale = max_dim / max(pil_img.width, pil_img.height)
            new_w = int(pil_img.width * scale)
            new_h = int(pil_img.height * scale)
            pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)

        # Skip small images (likely icons / decorations)
        if pil_img.width < 100 and pil_img.height < 100:
            return None

        buf = io.BytesIO()
        pil_img.save(buf, "PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def extract_pdf_formatted_html(file_path: str) -> str:
    """Extract PDF text as HTML preserving alignment, formatting, lists, tables, and images.

    Uses PyMuPDF (fitz) to read text blocks with position information.
    Detects left/right/center alignment from x-coordinates, bold/italic
    from font names, bullet/numbered lists from text patterns,
    table structures via PyMuPDF's built-in table detection, and
    embedded images rendered as base64 data URIs.
    """
    doc = fitz.open(file_path)
    page_html_parts = []

    for page in doc:
        pw = page.rect.width
        blocks = page.get_text("dict")["blocks"]

        # Detect tables and images
        excluded_regions = []  # (x0, y0, x1, y1)
        nontext_elements = []  # (y_start, html)

        # Tables
        try:
            table_finder = page.find_tables()
            for t in table_finder.tables:
                tx0, ty0, tx1, ty1 = t.bbox
                excluded_regions.append((tx0 - 2, ty0 - 2, tx1 + 2, ty1 + 2))
                table_html = _extract_table_html(t)
                if table_html:
                    nontext_elements.append((ty0, table_html))
        except Exception:
            pass

        # Images
        try:
            for img_info in page.get_image_info(xrefs=True):
                xref = img_info.get("xref")
                bbox = img_info.get("bbox")
                if not xref or not bbox:
                    continue
                uri = _image_to_data_uri(page, xref)
                if uri:
                    ix0, iy0, ix1, iy1 = bbox
                    excluded_regions.append((ix0 - 2, iy0 - 2, ix1 + 2, iy1 + 2))
                    # Align image based on its x-position matching text rules
                    img_center_x = (ix0 + ix1) / 2
                    if img_center_x > pw * 0.6:
                        img_align = "right"
                    elif img_center_x > pw * 0.3 and ix1 < pw * 0.7:
                        img_align = "center"
                    else:
                        img_align = "left"
                    img_style = "max-width:100%;height:auto"
                    if img_align == "left":
                        img_html = f'<div><img src="{uri}" style="{img_style}" alt="diagram"></div>'
                    else:
                        img_html = f'<div style="text-align:{img_align}"><img src="{uri}" style="{img_style}" alt="diagram"></div>'
                    nontext_elements.append((iy0, img_html))
        except Exception:
            pass

        def _in_excluded_region(x0, y0, x1, y1):
            for rx0, ry0, rx1, ry1 in excluded_regions:
                if x0 >= rx0 and y0 >= ry0 and x1 <= rx1 and y1 <= ry1:
                    return True
            return False

        raw_lines = []
        for block in blocks:
            if block["type"] != 0:
                continue
            for line in block["lines"]:
                lx0, ly0, lx1, ly1 = line["bbox"]
                if _in_excluded_region(lx0, ly0, lx1, ly1):
                    continue
                if lx0 > pw * 0.6:
                    align = "right"
                elif lx0 > pw * 0.3 and lx1 < pw * 0.7:
                    align = "center"
                else:
                    align = "left"

                text_parts = []
                for span in line["spans"]:
                    raw = span["text"]
                    if not raw:
                        continue
                    txt = raw.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    font = (span.get("font") or "").lower()
                    is_bold = "bold" in font or "bd" in font or "heavy" in font or "black" in font
                    is_italic = "italic" in font or "it" in font or "oblique" in font
                    if is_bold and is_italic:
                        txt = f"<strong><em>{txt}</em></strong>"
                    elif is_bold:
                        txt = f"<strong>{txt}</strong>"
                    elif is_italic:
                        txt = f"<em>{txt}</em>"
                    text_parts.append(txt)

                raw_lines.append([ly0, align, "".join(text_parts), lx0])

        # Build text/paragraph/list elements as (y_start, html) tuples
        elements = []

        if raw_lines:
            raw_lines.sort(key=lambda x: x[0])

            # Merge marker-only lines with the following content line
            merged = []
            skip_next = False
            for idx, (y, align, text, lx0) in enumerate(raw_lines):
                if skip_next:
                    skip_next = False
                    continue
                if _is_marker_only(text) and idx + 1 < len(raw_lines):
                    ny, nalign, ntext, nlx0 = raw_lines[idx + 1]
                    if ny - y < 10 and nlx0 > lx0:
                        merged.append([ny, align, text.strip() + " " + ntext, lx0])
                        skip_next = True
                        continue
                merged.append([y, align, text, lx0])
            raw_lines = merged

            i = 0
            while i < len(raw_lines):
                y, align, text, lx0 = raw_lines[i]
                list_type = _classify_line(text)

                if list_type:
                    items = []
                    cur_item = None
                    list_start_x0 = None
                    start_y = y
                    while i < len(raw_lines):
                        y, align, text, lx0 = raw_lines[i]
                        line_type = _classify_line(text)

                        if line_type == list_type:
                            if cur_item is not None:
                                items.append(" ".join(cur_item))
                            cur_item = [_strip_list_marker(text)]
                            list_start_x0 = lx0
                            i += 1
                        elif line_type is None and cur_item is not None:
                            gap = raw_lines[i][0] - raw_lines[i - 1][0]
                            if text.strip() and gap > 20:
                                break
                            if lx0 < list_start_x0 and text.strip():
                                break
                            cur_item.append(text)
                            i += 1
                        else:
                            break
                    if cur_item is not None:
                        items.append(" ".join(cur_item))
                    if items:
                        li_html = "".join(f"<li>{item}</li>" for item in items)
                        tag = "ol" if list_type == "ordered" else "ul"
                        elements.append((start_y, f"<{tag}>{li_html}</{tag}>"))
                else:
                    para_lines = [text]
                    start_y = y
                    i += 1
                    while i < len(raw_lines):
                        ny, nalign, ntext, nlx0 = raw_lines[i]
                        if _classify_line(ntext):
                            break
                        if nalign != align or ny - raw_lines[i - 1][0] > 20:
                            break
                        para_lines.append(ntext)
                        i += 1
                    inner = "<br>".join(para_lines)
                    if align == "left":
                        elements.append((start_y, f"<p>{inner}</p>"))
                    else:
                        elements.append((start_y, f'<p style="text-align:{align}">{inner}</p>'))

        # Merge text elements with non-text elements (tables, images) sorted by y position
        elements.extend(nontext_elements)
        elements.sort(key=lambda x: x[0])
        page_html_parts.extend(html for _, html in elements)

    doc.close()
    return "\n".join(page_html_parts)

def process_document(doc) -> str:
    """Process a DocumentData instance and extract text.

    For PDFs: extracts formatted HTML via PyMuPDF (preserving alignment,
    bold/italic). Also saves a layout-preserving .docx via pdf2docx
    for export. Falls back to OCR if the PDF has no selectable text.
    For images: uses Tesseract OCR with space preservation.
    """
    file_path = str(doc.file_path)
    TempStorage.update_status(doc.uuid, 'processing')

    try:
        if doc.is_pdf:
            text = extract_pdf_formatted_html(file_path)
            if len(text.strip()) < 100:
                logger.info(f"PDF seems scanned, switching to OCR for {doc.filename}")
                text = extract_scanned_pdf(file_path)

            # Save layout-preserving .docx for export (best effort)
            try:
                from pdf2docx import Converter
                cv = Converter(file_path)
                cv.convert(str(doc.docx_path), start=0, end=None)
                cv.close()
            except Exception as e:
                logger.warning(f"Could not create export .docx for {doc.filename}: {e}")

        elif doc.is_image:
            image = PILImage.open(file_path)
            text = extract_text_from_image(image)

        else:
            raise ValueError(f"Unsupported file type: {doc.file_extension}")

        TempStorage.update_status(doc.uuid, 'done')
        return text

    except Exception as e:
        TempStorage.update_status(doc.uuid, 'failed')
        logger.error(f"OCR failed for {doc.filename}: {e}")
        raise
