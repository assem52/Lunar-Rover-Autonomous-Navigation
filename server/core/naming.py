import re

_SAFE_NAME = re.compile(r'[^a-zA-Z0-9_-]+')


def sanitize_name(name: str, fallback: str = 'item') -> str:
    cleaned = _SAFE_NAME.sub('_', (name or '').strip())
    cleaned = cleaned.strip('_')
    return cleaned or fallback


