import io

from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings

ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf']


class UploadForm(forms.Form):
    file = forms.FileField(widget=forms.FileInput(attrs={
        'class': 'hidden',
        'id': 'file-upload',
        'accept': ','.join(ALLOWED_EXTENSIONS),
    }))

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("Please select a file to upload.")

        if file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            max_size_mb = settings.FILE_UPLOAD_MAX_MEMORY_SIZE / (1024 * 1024)
            raise ValidationError(f"File size must be under {max_size_mb:.0f}MB.")

        ext = file.name.lower()
        if not any(ext.endswith(allowed) for allowed in ALLOWED_EXTENSIONS):
            raise ValidationError(
                f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        file.seek(0)
        file_bytes = file.read()

        if file_bytes.startswith(b'%PDF-'):
            if ext.endswith('.pdf'):
                file.seek(0)
                return file
            raise ValidationError("File content is a PDF, but extension is incorrect.")

        try:
            from PIL import Image
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()
            if img.format not in ['JPEG', 'PNG', 'BMP', 'TIFF']:
                raise ValidationError(f"Unsupported image format: {img.format}")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Invalid image file: {e}")

        file.seek(0)
        return file
