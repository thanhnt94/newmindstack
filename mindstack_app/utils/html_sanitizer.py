"""Lightweight HTML sanitizer tailored for the Mindstack rich text editor."""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from typing import Iterable
from urllib.parse import urlsplit

# Allowed tags closely mirror modern WYSIWYG capabilities while staying safe.
ALLOWED_TAGS: Iterable[str] = {
    'a', 'abbr', 'b', 'blockquote', 'br', 'code', 'del', 'div', 'em', 'figcaption',
    'figure', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hr', 'i', 'iframe', 'img',
    'li', 'ol', 'p', 'picture', 'pre', 'section', 'small', 'span', 'strong',
    'sub', 'sup', 'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u',
    'ul', 'video', 'audio', 'source'
}

VOID_TAGS = {'br', 'hr', 'img', 'source'}

ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title', 'target', 'rel', 'class'},
    'audio': {'controls', 'src', 'loop', 'preload', 'class'},
    'div': {'class', 'style'},
    'figure': {'class', 'style'},
    'figcaption': {'class', 'style'},
    'iframe': {'src', 'width', 'height', 'allow', 'allowfullscreen', 'loading', 'title', 'class'},
    'img': {'alt', 'src', 'title', 'width', 'height', 'class', 'style', 'loading'},
    'li': {'class'},
    'ol': {'class'},
    'p': {'class', 'style'},
    'picture': {'class'},
    'section': {'class', 'style'},
    'span': {'class', 'style'},
    'table': {'class', 'style'},
    'tbody': {'class'},
    'td': {'class', 'colspan', 'rowspan', 'style'},
    'tfoot': {'class'},
    'th': {'class', 'colspan', 'rowspan', 'scope', 'style'},
    'thead': {'class'},
    'tr': {'class'},
    'video': {'class', 'controls', 'src', 'poster', 'width', 'height', 'preload', 'playsinline'},
}

ALLOWED_STYLES = {
    'background-color', 'border', 'border-color', 'border-style', 'border-width',
    'color', 'display', 'font-size', 'font-style', 'font-weight', 'height',
    'line-height', 'margin', 'margin-bottom', 'margin-left', 'margin-right',
    'margin-top', 'padding', 'padding-bottom', 'padding-left', 'padding-right',
    'padding-top', 'text-align', 'text-decoration', 'width', 'max-width'
}

URL_ATTRIBUTES = {'href', 'src'}
ALLOWED_PROTOCOLS = {'http', 'https', 'mailto', 'tel', 'data'}


def _is_safe_url(value: str) -> bool:
    value = value.strip()
    if not value:
        return False
    if value.startswith(('#', '/')):
        return True
    parts = urlsplit(value)
    if not parts.scheme:
        return True
    scheme = parts.scheme.lower()
    if scheme == 'data':
        # Chỉ cho phép data URI dành cho hình ảnh, audio hoặc video.
        return parts.path.lower().startswith(('image/', 'audio/', 'video/'))
    return scheme in ALLOWED_PROTOCOLS


def _sanitize_style(value: str) -> str:
    cleaned_rules: list[str] = []
    for rule in value.split(';'):
        if ':' not in rule:
            continue
        prop, val = rule.split(':', 1)
        prop = prop.strip().lower()
        if prop not in ALLOWED_STYLES:
            continue
        val = val.strip()
        if not val:
            continue
        cleaned_rules.append(f"{prop}: {val}")
    return '; '.join(cleaned_rules)


class _RichTextSanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self._output: list[str] = []
        self._open_tags: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in ALLOWED_TAGS:
            return

        allowed_attrs = ALLOWED_ATTRIBUTES.get(tag, set())
        cleaned_attrs: list[str] = []
        for attr_name, attr_value in attrs:
            if attr_name not in allowed_attrs or attr_value is None:
                continue

            attr_value = attr_value.strip()
            if attr_name in URL_ATTRIBUTES and not _is_safe_url(attr_value):
                continue

            if attr_name == 'style':
                attr_value = _sanitize_style(attr_value)
                if not attr_value:
                    continue

            escaped = escape(attr_value, quote=True)
            cleaned_attrs.append(f'{attr_name}="{escaped}"')

        attr_string = ''
        if cleaned_attrs:
            attr_string = ' ' + ' '.join(cleaned_attrs)

        self._output.append(f'<{tag}{attr_string}>')
        if tag not in VOID_TAGS:
            self._open_tags.append(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag not in ALLOWED_TAGS or tag in VOID_TAGS:
            return
        for index in range(len(self._open_tags) - 1, -1, -1):
            if self._open_tags[index] == tag:
                del self._open_tags[index]
                self._output.append(f'</{tag}>')
                break

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # Treat as start tag followed by immediate end for void tags.
        self.handle_starttag(tag, attrs)
        if tag in VOID_TAGS and self._output:
            # Replace the last appended start tag with a self-closing variant.
            last = self._output.pop()
            if last.startswith(f'<{tag}') and last.endswith('>'):
                self._output.append(last[:-1] + ' />')
            else:
                self._output.append(last)

    def handle_data(self, data: str) -> None:
        self._output.append(escape(data))

    def handle_entityref(self, name: str) -> None:
        self._output.append(f'&{name};')

    def handle_charref(self, name: str) -> None:
        self._output.append(f'&#{name};')

    def get_html(self) -> str:
        return ''.join(self._output)


def sanitize_rich_text(raw_html: str | None) -> str:
    """Sanitize rich-text HTML content generated by the editor."""

    if not raw_html:
        return ''

    parser = _RichTextSanitizer()
    parser.feed(raw_html)
    parser.close()
    return parser.get_html()

