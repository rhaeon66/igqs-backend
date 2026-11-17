"""Allowlist cleaner for article HTML written in the staff editor.

Plain text is returned unchanged, so existing paragraphs keep their line
breaks. Only tags the public site knows how to show are kept, and links
and colours are restricted so a saved article cannot run script.
"""

import re
from html.parser import HTMLParser

_VOID = {"br", "hr", "img"}
_BLOCKS_WITH_STYLE = {"p", "h1", "h2", "h3", "li", "blockquote", "td", "th", "div", "span"}
_ALLOWED = {
    "p": set(),
    "br": set(),
    "strong": set(),
    "b": set(),
    "em": set(),
    "i": set(),
    "u": set(),
    "s": set(),
    "strike": set(),
    "h1": set(),
    "h2": set(),
    "h3": set(),
    "ul": set(),
    "ol": set(),
    "li": set(),
    "blockquote": set(),
    "hr": set(),
    "a": {"href", "title"},
    "img": {"src", "alt", "title"},
    "table": set(),
    "thead": set(),
    "tbody": set(),
    "tr": set(),
    "th": {"colspan", "rowspan"},
    "td": {"colspan", "rowspan"},
    "span": set(),
    "div": set(),
}
_COLOR = re.compile(
    r"^(?:#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6}|rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\))$"
)
_SIZE = re.compile(r"^(\d+(?:\.\d+)?)(px|rem|em|%)$")
_TAG = re.compile(r"</?[a-zA-Z][^>]*>")


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _safe_url(value: str) -> str:
    raw = value.strip()
    lowered = raw.lower()
    if lowered.startswith(("https://", "http://", "mailto:", "tel:", "/")) and not lowered.startswith("//"):
        return raw.replace('"', "%22")
    return ""


def _clean_style(value: str) -> str:
    kept = []
    for chunk in value.split(";"):
        if ":" not in chunk:
            continue
        prop, raw = chunk.split(":", 1)
        prop = prop.strip().lower()
        raw = raw.strip()
        if prop == "text-align" and raw.lower() in {"left", "center", "right", "justify"}:
            kept.append(f"text-align: {raw.lower()}")
        elif prop in {"color", "background-color"} and _COLOR.match(raw):
            kept.append(f"{prop}: {raw}")
        elif prop == "font-size" and (match := _SIZE.match(raw)):
            size = float(match.group(1))
            unit = match.group(2)
            if unit == "px" and 12 <= size <= 48:
                kept.append(f"font-size: {raw}")
            elif unit in {"rem", "em"} and 0.75 <= size <= 3:
                kept.append(f"font-size: {raw}")
            elif unit == "%" and 75 <= size <= 200:
                kept.append(f"font-size: {raw}")
    return "; ".join(kept)


class _Cleaner(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed", "form"}:
            self.skip += 1
            return
        if self.skip or tag not in _ALLOWED:
            return
        allowed = set(_ALLOWED[tag])
        if tag in _BLOCKS_WITH_STYLE:
            allowed.add("style")
        parts = []
        for name, value in attrs:
            name = name.lower()
            if name not in allowed or value is None:
                continue
            if name in {"href", "src"}:
                value = _safe_url(value)
                if not value:
                    continue
            elif name == "style":
                value = _clean_style(value)
                if not value:
                    continue
            elif name in {"colspan", "rowspan"}:
                if not value.isdigit() or int(value) > 12:
                    continue
            parts.append(f'{name}="{_escape(value)}"')
        rendered = " ".join(parts)
        if tag == "a":
            parts.append('rel="noopener noreferrer"')
            rendered = " ".join(parts)
        gap = " " if rendered else ""
        if tag in _VOID:
            self.out.append(f"<{tag}{gap}{rendered}>")
        else:
            self.out.append(f"<{tag}{gap}{rendered}>")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"script", "style", "iframe", "object", "embed", "form"}:
            if self.skip:
                self.skip -= 1
            return
        if self.skip or tag not in _ALLOWED or tag in _VOID:
            return
        self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self.skip:
            return
        self.out.append(_escape(data))


def sanitize_html(value: str) -> str:
    """Return safe HTML, or the original string when it is not HTML."""
    if not value or not _TAG.search(value):
        return value or ""
    cleaner = _Cleaner()
    cleaner.feed(value)
    cleaner.close()
    html = "".join(cleaner.out).strip()
    if not re.sub(r"<[^>]+>", "", html).strip() and "<img" not in html:
        return ""
    return html
