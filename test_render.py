import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'ocr_project.settings'

import django
django.setup()

from django.test import RequestFactory
from django.urls import reverse
from apps.ocr.views import document_detail
from apps.ocr.storage import TempStorage

factory = RequestFactory()
request = factory.get('/')
request.META['CSRF_COOKIE'] = 'test'

doc_uuid = 'ec00c060-97a7-4315-a913-464ef0284be7'
doc = TempStorage.get(doc_uuid)
print(f'Status: {doc.status}')
text = TempStorage.get_text(doc_uuid)
print(f'Text on disk: {repr(text[:200])}')
print()

response = document_detail(request, doc_uuid)
html = response.content.decode('utf-8')

# Find the textarea content
import re
match = re.search(r'<textarea[^>]*>([\s\S]*?)</textarea>', html)
if match:
    content = match.group(1)
    print(f'Textarea content: {repr(content[:300])}')
    
    # Decode HTML entities
    import html
    decoded = html.unescape(content)
    print(f'Decoded: {repr(decoded[:300])}')
