"""
Text post-processing for OCR output cleanup.

Removes noise characters, normalizes whitespace,
and applies basic formatting fixes.
"""

import re


def clean_text(raw_text: str) -> str:
    """
    Clean and normalize raw OCR output text.
    
    Relaxes character filtering to support Unicode and HTML,
    but cleans up excessive whitespace and blank lines.
    
    Args:
        raw_text: Raw text or HTML from OCR engine.
    
    Returns:
        Cleaned string.
    """
    if not raw_text:
        return ""

    # Relax filtering to support Unicode (common accents, etc.)
    # We remove control characters but keep most printables + HTML tags
    text = "".join(
        ' ' if not ch.isprintable() and ch not in "\n\t\r\f" else ch
        for ch in raw_text
    )

    # If it's HTML (contains tags), we use a lighter cleaning to avoid breaking structure
    if '<' in text and '>' in text:
        # Standardize newlines
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Remove excessive empty lines only
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        return text.strip()

    # Standard plain text cleaning
    # Normalize multiple spaces (preserve newlines)
    text = re.sub(r'[^\S\n]+', ' ', text)
    # Remove excessive blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Strip each line
    lines = [line.strip() for line in text.splitlines()]
    text = '\n'.join(lines)
    
    return text.strip()
