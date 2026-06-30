"""
Image preprocessing for better OCR accuracy.

Applies grayscale conversion, adaptive thresholding,
and noise removal via morphological operations.
"""

import cv2
import numpy as np
from PIL import Image


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Apply preprocessing pipeline to improve OCR accuracy.
    
    Steps:
        1. Convert to grayscale
        2. Apply adaptive thresholding
        3. Remove noise with morphological operations
    
    Args:
        image: PIL Image to preprocess.
    
    Returns:
        Preprocessed PIL Image.
    """
    # Convert PIL Image to OpenCV format (numpy array)
    img_array = np.array(image)

    # Convert to grayscale if not already
    if len(img_array.shape) == 3:
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    else:
        gray = img_array

    # Apply adaptive thresholding for better contrast
    thresh = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=11,
        C=2,
    )

    # Remove noise with morphological operations
    kernel = np.ones((3, 3), np.uint8)
    cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)

    # Convert back to PIL Image
    return Image.fromarray(cleaned)
