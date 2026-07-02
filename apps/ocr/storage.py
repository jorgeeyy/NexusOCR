import json
import os
import shutil
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


def get_temp_root() -> Path:
    """Return the temp storage root directory."""
    root = Path(settings.BASE_DIR) / 'temp'
    root.mkdir(parents=True, exist_ok=True)
    return root


@dataclass
class DocumentData:
    uuid: str
    filename: str
    status: str  # 'pending', 'processing', 'done', 'failed'
    created_at: float
    file_type: str = ''  # 'pdf', 'image'

    @property
    def dir_path(self) -> Path:
        return get_temp_root() / self.uuid

    @property
    def file_path(self) -> Path:
        return self.dir_path / f'original{self.file_extension}'

    @property
    def file_extension(self) -> str:
        return os.path.splitext(self.filename)[1].lower()

    @property
    def is_pdf(self) -> bool:
        return self.file_extension == '.pdf'

    @property
    def is_image(self) -> bool:
        return self.file_extension in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']

    @property
    def text_path(self) -> Path:
        return self.dir_path / 'extracted_text.txt'

    @property
    def docx_path(self) -> Path:
        return self.dir_path / 'converted.docx'

    @property
    def meta_path(self) -> Path:
        return self.dir_path / 'meta.json'

    def save_meta(self):
        meta = {
            'uuid': self.uuid,
            'filename': self.filename,
            'status': self.status,
            'created_at': self.created_at,
            'file_type': self.file_type,
        }
        self.dir_path.mkdir(parents=True, exist_ok=True)
        self.meta_path.write_text(json.dumps(meta), encoding='utf-8')

    @classmethod
    def load_from_dir(cls, doc_uuid: str) -> 'DocumentData | None':
        meta_path = get_temp_root() / doc_uuid / 'meta.json'
        if not meta_path.exists():
            return None
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            return cls(
                uuid=meta['uuid'],
                filename=meta['filename'],
                status=meta['status'],
                created_at=meta['created_at'],
                file_type=meta.get('file_type', ''),
            )
        except (json.JSONDecodeError, KeyError):
            return None


class TempStorage:

    @staticmethod
    def create(filename: str, file_data: bytes, file_type: str = '') -> DocumentData:
        doc_uuid = str(uuid.uuid4())
        doc = DocumentData(
            uuid=doc_uuid,
            filename=filename,
            status='pending',
            created_at=time.time(),
            file_type=file_type,
        )
        doc.dir_path.mkdir(parents=True, exist_ok=True)
        doc.file_path.write_bytes(file_data)
        doc.save_meta()
        return doc

    @staticmethod
    def get(doc_uuid: str) -> DocumentData | None:
        return DocumentData.load_from_dir(doc_uuid)

    @staticmethod
    def get_text(doc_uuid: str) -> str:
        doc = TempStorage.get(doc_uuid)
        if doc and doc.text_path.exists():
            return doc.text_path.read_text(encoding='utf-8')
        return ''

    @staticmethod
    def update_text(doc_uuid: str, text: str):
        doc = TempStorage.get(doc_uuid)
        if doc:
            doc.text_path.write_text(text, encoding='utf-8')

    @staticmethod
    def update_status(doc_uuid: str, status: str):
        doc = TempStorage.get(doc_uuid)
        if doc:
            doc.status = status
            doc.save_meta()

    @staticmethod
    def delete(doc_uuid: str):
        doc_dir = get_temp_root() / doc_uuid
        if doc_dir.exists() and doc_dir.is_dir():
            shutil.rmtree(doc_dir, ignore_errors=True)

    @staticmethod
    def cleanup(max_age_minutes: int = 60):
        root = get_temp_root()
        if not root.exists():
            return
        cutoff = time.time() - (max_age_minutes * 60)
        for doc_dir in root.iterdir():
            if not doc_dir.is_dir():
                continue
            meta_path = doc_dir / 'meta.json'
            if meta_path.exists():
                try:
                    meta = json.loads(meta_path.read_text(encoding='utf-8'))
                    if meta.get('created_at', 0) < cutoff:
                        shutil.rmtree(doc_dir, ignore_errors=True)
                except (json.JSONDecodeError, KeyError):
                    shutil.rmtree(doc_dir, ignore_errors=True)
            else:
                shutil.rmtree(doc_dir, ignore_errors=True)
