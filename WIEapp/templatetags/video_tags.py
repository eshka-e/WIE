from django import template
from django.template.defaultfilters import stringfilter
import re

register = template.Library()


@register.filter
@stringfilter
def youtube_embed(value):
    """Преобразует ссылку YouTube в embed URL"""
    if not value:
        return value

    # YouTube patterns
    patterns = [
        r'youtu\.be/([^?&]+)',
        r'youtube\.com/watch\?v=([^&]+)',
        r'youtube\.com/embed/([^?&]+)',
        r'youtube\.com/v/([^?&]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, value)
        if match:
            video_id = match.group(1)
            return f'https://www.youtube.com/embed/{video_id}'

    # Vimeo
    vimeo_match = re.search(r'vimeo\.com/(\d+)', value)
    if vimeo_match:
        video_id = vimeo_match.group(1)
        return f'https://player.vimeo.com/video/{video_id}'

    return value