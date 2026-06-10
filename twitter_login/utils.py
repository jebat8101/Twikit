import json
from enum import Enum
from typing import Sequence, Type, TypeVar


def optional_chaining(dict_, *chain, default = None):
    """
    Implementation of optional chaining.
    a?.b?.c =  optional_chaining(a, 'b', 'c')
    """
    cur = dict_
    for key in chain:
        if not isinstance(cur, dict):
            return default
        if key not in cur:
            return default
        cur = cur[key]
    return cur


T = TypeVar('T', bound=Enum)


def sort_enum_values(values: Sequence[T], enum_class: Type[T]) -> list[T]:
    """
    Sorts enum values by definition order.
    Note that it always returns a list.
    """
    class_values = enum_class.__members__.values()
    for v in values:
        if v not in class_values:
            raise ValueError(f'Unknown enum member for {enum_class.__name__}: {v}')

    value_index = {v: i for i, v in enumerate(class_values)}
    return sorted(values, key=value_index.get)


def safe_convert(obj, type):
    if obj is None:
        return None
    try:
        return type(obj)
    except (TypeError, ValueError):
        return None


def log_json(obj, path = 'log.json'):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)


def parse_cookies_file(text: str) -> dict[str, str]:
    """Parse cookies from JSON ``{name: value}`` or Netscape export format."""
    text = text.strip()
    if not text:
        raise ValueError(
            'cookies file is empty. Log in to x.com, export cookies with the '
            'export_cookies extension (or DevTools), and save as cookies.json '
            'next to run.py.'
        )

    try:
        cookies = json.loads(text)
    except json.JSONDecodeError:
        cookies = _parse_netscape_cookies(text)

    if not isinstance(cookies, dict):
        raise ValueError('cookies file must be a JSON object mapping cookie names to values.')
    if not cookies:
        raise ValueError('cookies file contains no cookies.')

    return {str(k): str(v) for k, v in cookies.items()}


def _parse_netscape_cookies(text: str) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]
    if not cookies:
        raise ValueError(
            'cookies file is not valid JSON or Netscape format. '
            'Use the export_cookies extension or save {"auth_token": "...", "ct0": "..."}.'
        )
    return cookies
