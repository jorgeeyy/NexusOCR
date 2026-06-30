from django import forms
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import Document

ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.pdf']


class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'hidden',
                'id': 'file-upload',
                'accept': ','.join(ALLOWED_EXTENSIONS),
            })
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            raise ValidationError("Please select a file to upload.")

        # Check file size
        if file.size > settings.FILE_UPLOAD_MAX_MEMORY_SIZE:
            max_size_mb = settings.FILE_UPLOAD_MAX_MEMORY_SIZE / (1024 * 1024)
            raise ValidationError(f"File size must be under {max_size_mb:.0f}MB.")

        # Check extension first as a quick filter
        ext = file.name.lower()
        if not any(ext.endswith(allowed) for allowed in ALLOWED_EXTENSIONS):
            raise ValidationError(
                f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
            
        # Validate actual file content (MIME type / magic numbers)
        file.seek(0)
        file_header = file.read(1024)
        file.seek(0)

        is_valid = False
        
        # Check if it's a PDF by magic number
        if file_header.startswith(b'%PDF-'):
            if ext.endswith('.pdf'):
                is_valid = True
            else:
                raise ValidationError("File content is a PDF, but extension is incorrect.")
                
        # Check if it's a valid image using Pillow
        else:
            try:
                from PIL import Image
                import io
                
                # Pillow requires seek(0) before opening
                img = Image.open(io.BytesIO(file_header))
                img.verify() # Verify it's a valid image without decoding the whole thing
                
                # Verify format matches our allowed list
                if img.format in ['JPEG', 'PNG', 'BMP', 'TIFF']:
                    is_valid = True
                else:
                    raise ValidationError(f"Unsupported image format: {img.format}")
                    
            except ValidationError:
                raise
            except Exception as e:
                raise ValidationError(f"Invalid image file: {e}")
                
        if not is_valid:
            raise ValidationError("Invalid file content. The file does not appear to be a valid image or PDF.")

        return file
