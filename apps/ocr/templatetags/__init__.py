from django import template
from django.utils.safestring import mark_safe

import bleach

register = template.Library()

ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'ul', 'ol', 'li', 'pre', 'blockquote', 'hr',
    'strong', 'em', 'b', 'i', 'u', 's',
]

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES['*'] = ['class', 'style']


@register.filter
def sanitize_html(value):
    """Sanitize HTML to prevent XSS while preserving safe formatting."""
    if not value:
        return ''
    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True,
    )
    return mark_safe(cleaned)
