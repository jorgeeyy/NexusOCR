from django import template
from django.template.defaultfilters import linebreaks
from django.utils.safestring import mark_safe

import bleach
from bleach.css_sanitizer import CSSSanitizer

register = template.Library()

ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'div', 'span', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'ul', 'ol', 'li', 'pre', 'blockquote', 'hr',
    'strong', 'em', 'b', 'i', 'u', 's',
]

ALLOWED_ATTRIBUTES = dict(bleach.ALLOWED_ATTRIBUTES)
ALLOWED_ATTRIBUTES['*'] = ['class', 'style']

CSS_SANITIZER = CSSSanitizer(allowed_css_properties=[
    'text-align', 'text-decoration', 'font-weight', 'font-style',
])


@register.filter
def sanitize_html(value):
    """Sanitize HTML to prevent XSS while preserving safe formatting."""
    if not value:
        return ''
    cleaned = bleach.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        css_sanitizer=CSS_SANITIZER,
        strip=True,
    )
    return mark_safe(cleaned)


@register.filter
def format_for_editor(value):
    """Convert stored text to HTML for the editor.

    If the text is already HTML (contains tags), just sanitize it.
    If it's plain text, apply linebreaks first then sanitize.
    """
    if not value:
        return ''
    if '<' in value and '>' in value:
        cleaned = bleach.clean(
            value,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            css_sanitizer=CSS_SANITIZER,
            strip=True,
        )
        return mark_safe(cleaned)
    return sanitize_html(linebreaks(value))
