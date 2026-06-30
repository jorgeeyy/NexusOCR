from django.apps import AppConfig


class OcrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ocr'
    label = 'ocr'

    def ready(self):
        from .storage import TempStorage
        TempStorage.cleanup()
