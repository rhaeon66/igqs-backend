import logging
import math
import re
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from PIL import Image as PilImage
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, shapeStr
from reportlab.pdfgen import canvas

from content.models import SiteSettings

logger = logging.getLogger(__name__)

FOREST = HexColor("#0f3d30")
GOLD = HexColor("#c4a35a")
GOLD_SOFT = HexColor("#e8d7a8")
# Gold is too light for small text on white/cream (2.4:1); labels use this.
LABEL = HexColor("#7a6329")
INK = HexColor("#1c241f")
MUTED = HexColor("#5c6b66")
CREAM = HexColor("#f7f1e3")
RULE = HexColor("#e4d5b3")
HAIRLINE = HexColor("#efe6d2")

FONT_DIR = Path(__file__).resolve().parent / "fonts"
# Used when no logo has been uploaded in Site settings (same crest as the website).
BUNDLED_LOGO = Path(__file__).resolve().parent / "assets" / "igqs-logo.png"

_FONTS_READY = False
# All faces ship with the app (SIL OFL, see fonts/*OFL.txt), so the receipt
# looks the same on any server. Inter for English, Noto Sans Bengali for
# Bangla, Noto Sans Mono for transaction IDs. The Helvetica values are only
# a last resort if a file is missing.
LATIN = "Helvetica"
LATIN_MEDIUM = "Helvetica"
LATIN_SEMIBOLD = "Helvetica-Bold"
LATIN_BOLD = "Helvetica-Bold"
BENGALI = "Helvetica"
BENGALI_MEDIUM = "Helvetica"
BENGALI_BOLD = "Helvetica-Bold"
MONO = "Courier"
SERIF_BOLD = "Times-Bold"
SERIF_ITALIC = "Times-Italic"


def _register_one(name: str, path: Path) -> bool:
    if name in pdfmetrics.getRegisteredFontNames():
        return True
    try:
        pdfmetrics.registerFont(TTFont(name, str(path)))
    except Exception:
        logger.warning("Could not register receipt font %s from %s", name, path)
        return False
    return True


def _register_fonts() -> None:
    global _FONTS_READY, LATIN, LATIN_MEDIUM, LATIN_SEMIBOLD, LATIN_BOLD
    global BENGALI, BENGALI_MEDIUM, BENGALI_BOLD, MONO, SERIF_BOLD, SERIF_ITALIC
    if _FONTS_READY:
        return
    faces = {
        "LATIN": ("IGQSInter", "Inter-Regular.ttf"),
        "LATIN_MEDIUM": ("IGQSInter-Medium", "Inter-Medium.ttf"),
        "LATIN_SEMIBOLD": ("IGQSInter-SemiBold", "Inter-SemiBold.ttf"),
        "LATIN_BOLD": ("IGQSInter-Bold", "Inter-Bold.ttf"),
        "BENGALI": ("IGQSBengali", "NotoSansBengali-Regular.ttf"),
        "BENGALI_MEDIUM": ("IGQSBengali-Medium", "NotoSansBengali-Medium.ttf"),
        "BENGALI_BOLD": ("IGQSBengali-Bold", "NotoSansBengali-Bold.ttf"),
        "MONO": ("IGQSMono", "NotoSansMono-Medium.ttf"),
        "SERIF_BOLD": ("IGQSSerif-Bold", "NotoSerif-Bold.ttf"),
        "SERIF_ITALIC": ("IGQSSerif-Italic", "NotoSerif-Italic.ttf"),
    }
    chosen = {}
    for key, (name, filename) in faces.items():
        if _register_one(name, FONT_DIR / filename):
            chosen[key] = name
    if "BENGALI" not in chosen and _register_one("IGQSBornomala", FONT_DIR / "Bornomala-Regular.ttf"):
        chosen["BENGALI"] = "IGQSBornomala"
    if "BENGALI" not in chosen:
        logger.warning("No Bengali font available for receipts; Bengali names will not render.")
    chosen.setdefault("BENGALI_MEDIUM", chosen.get("BENGALI", BENGALI))
    chosen.setdefault("BENGALI_BOLD", chosen["BENGALI_MEDIUM"])

    LATIN = chosen.get("LATIN", LATIN)
    LATIN_MEDIUM = chosen.get("LATIN_MEDIUM", LATIN_MEDIUM)
    LATIN_SEMIBOLD = chosen.get("LATIN_SEMIBOLD", LATIN_SEMIBOLD)
    LATIN_BOLD = chosen.get("LATIN_BOLD", LATIN_BOLD)
    BENGALI = chosen.get("BENGALI", BENGALI)
    BENGALI_MEDIUM = chosen["BENGALI_MEDIUM"]
    BENGALI_BOLD = chosen["BENGALI_BOLD"]
    MONO = chosen.get("MONO", MONO)
    SERIF_BOLD = chosen.get("SERIF_BOLD", SERIF_BOLD)
    SERIF_ITALIC = chosen.get("SERIF_ITALIC", SERIF_ITALIC)

    if BENGALI != "Helvetica" and not pdfmetrics.getFont(BENGALI).shapable:
        logger.warning(
            "uharfbuzz is not installed; Bengali on receipts will print with "
            "broken conjuncts and vowel signs. pip install uharfbuzz."
        )
    _FONTS_READY = True


# Bengali block plus the joiners and dandas that belong inside Bengali runs.
_BENGALI_RUN = re.compile(r"([ঀ-৿‌‍।॥]+)")


def _has_bengali(text: str) -> bool:
    return any("ঀ" <= char <= "৿" for char in text)


def _font_for(text: str, bold: bool = False) -> str:
    if _has_bengali(text):
        return BENGALI_MEDIUM if bold else BENGALI
    return LATIN_BOLD if bold else LATIN


def _prepare(text: str, font: str, size: float):
    """Returns (drawable text, width).

    Bengali has to be shaped: vowel signs reorder (ি is typed after the
    consonant but drawn before it) and consonants join into conjuncts (ক্ষ).
    Drawn code point by code point, আদর্শ prints as "আদরশ". ReportLab only
    shapes via HarfBuzz (uharfbuzz), and its drawString can't do it on its
    own here, so the text is shaped up front and drawn as glyphs.
    """
    if _has_bengali(text) and pdfmetrics.getFont(font).shapable:
        shaped = shapeStr(text, font, size, force=True)
        data = getattr(shaped, "__shapeData__", None)
        if data:
            return shaped, sum(glyph.x_advance for glyph in data) * size / 1000
    return text, pdfmetrics.stringWidth(text, font, size)


def _runs(word: str, latin_font: str, bengali_font: str):
    """Splits a word into (text, font) runs by script, so "(আব্দুর" draws the
    bracket in Inter and the name in Noto Sans Bengali (which has no Latin)."""
    for part in _BENGALI_RUN.split(word):
        if part:
            yield part, (bengali_font if _has_bengali(part) else latin_font)


def _word_width(word: str, latin_font: str, bengali_font: str, size: float) -> float:
    return sum(_prepare(text, font, size)[1] for text, font in _runs(word, latin_font, bengali_font))


def _draw_text(c, x: float, y: float, text: str, font: str, size: float) -> float:
    drawable, width = _prepare(text, font, size)
    c.setFont(font, size)
    c.drawString(x, y, drawable)
    return width


def _draw_word(c, x, y, word, latin_font, bengali_font, size) -> float:
    start = x
    for text, font in _runs(word, latin_font, bengali_font):
        x += _draw_text(c, x, y, text, font, size)
    return x - start


def _bengali_counterpart(latin_font: str) -> str:
    if latin_font == LATIN_BOLD:
        return BENGALI_BOLD
    return BENGALI_MEDIUM if latin_font in (LATIN_MEDIUM, LATIN_SEMIBOLD) else BENGALI


def _split_long(word: str, latin_font: str, bengali_font: str, size: float, max_width: float) -> list[str]:
    """Breaks a word too wide for the column (an email, a long ID): after
    '.', '@', '-', '_' or '/' where possible, otherwise between characters."""
    if _has_bengali(word) or _word_width(word, latin_font, bengali_font, size) <= max_width:
        return [word]
    pieces, current, last_break = [], "", -1
    for char in word:
        if current and _word_width(current + char, latin_font, bengali_font, size) > max_width:
            if last_break > 0:
                pieces.append(current[:last_break])
                current = current[last_break:]
            else:
                pieces.append(current)
                current = ""
            last_break = -1
        current += char
        if char in ".@-_/":
            last_break = len(current)
    if current:
        pieces.append(current)
    return pieces


def _wrap(text: str, latin_font: str, size: float, max_width: float) -> list[list[str]]:
    bengali_font = _bengali_counterpart(latin_font)
    space_width = pdfmetrics.stringWidth(" ", latin_font, size)
    lines: list[list[str]] = []
    current: list[str] = []
    current_width = 0.0
    # Split on ordinary spaces only: a no-break space keeps a phone number
    # or other unit together (str.split() would break on it too).
    words = [
        piece
        for word in re.split(r"[ \t\n]+", text.strip())
        if word
        for piece in _split_long(word, latin_font, bengali_font, size, max_width)
    ]
    for word in words:
        word_width = _word_width(word, latin_font, bengali_font, size)
        extra = (space_width if current else 0) + word_width
        if current and current_width + extra > max_width:
            lines.append(current)
            current, current_width = [word], word_width
        else:
            current.append(word)
            current_width += extra
    if current:
        lines.append(current)
    return lines


def _leading(text: str, size: float) -> float:
    # Bengali stacks vowel signs above and below the line; it needs more room.
    return size * (1.6 if _has_bengali(text) else 1.35)


def _draw_lines(c, lines, x, y, latin_font, size, leading) -> None:
    bengali_font = _bengali_counterpart(latin_font)
    space_width = pdfmetrics.stringWidth(" ", latin_font, size)
    for i, line_words in enumerate(lines):
        cursor_x = x
        for j, word in enumerate(line_words):
            if j:
                cursor_x += space_width
            cursor_x += _draw_word(c, cursor_x, y - i * leading, word, latin_font, bengali_font, size)


def _draw_wrapped(c, text, x, y, max_width, font, size, color=INK, leading=None):
    """Word-wraps and draws text; returns the baseline of the last line."""
    c.setFillColor(color)
    leading = leading or _leading(text, size)
    lines = _wrap(text, font, size, max_width)
    if not lines:
        return y
    _draw_lines(c, lines, x, y, font, size, leading)
    return y - (len(lines) - 1) * leading


def _draw_label(c, x: float, y: float, text: str, size: float = 7.2, color=LABEL) -> None:
    # Labels are English-only, so tracking is safe here (never on Bengali).
    c.setFillColor(color)
    c.setFont(LATIN_MEDIUM, size)
    c.drawString(x, y, text.upper(), charSpace=0.7)


def school_info() -> dict:
    site = SiteSettings.objects.first()
    if not site:
        return {
            "name": "Ideal Global Qur'anic School",
            "name_bn": "আদর্শ গ্লোবাল কুরআনিক স্কুল",
            "address": "Dhaka, Bangladesh",
            "phones": "",
            "email": "info@igqs.edu.bd",
            "logo_path": None,
        }
    phones = site.phone_primary
    if site.phone_secondary:
        phones = f"{site.phone_primary}  ·  {site.phone_secondary}"
    logo_path = None
    if site.logo:
        logo_path = site.logo.path
    return {
        "name": site.school_name_en,
        "name_bn": site.school_name_bn,
        "address": site.address_en,
        "phones": phones,
        "email": site.email,
        "logo_path": logo_path,
    }


def _draw_mark(c: canvas.Canvas, x: float, y: float, size: float) -> None:
    c.setFillColor(GOLD)
    c.circle(x + size / 2, y + size / 2, size / 2, fill=1, stroke=0)
    c.setFillColor(FOREST)
    c.circle(x + size / 2, y + size / 2, size / 2 - 3, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(LATIN_BOLD, 9)
    c.drawCentredString(x + size / 2, y + size / 2 - 3, "IGQS")


def _logo_reader(path: Path) -> ImageReader:
    """Load a crest for PDF drawing with a real alpha channel.

    Uploaded JPGs often ship with a solid black square behind the circle;
    ReportLab would paint that square on the green header. Near-black pixels
    are cleared (the navy ring keeps its blue channel, so it stays).
    """
    image = PilImage.open(path).convert("RGBA")
    pixels = [
        (0, 0, 0, 0) if (pixel[0] < 18 and pixel[1] < 18 and pixel[2] < 18) else pixel
        for pixel in image.getdata()
    ]
    image.putdata(pixels)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return ImageReader(buffer)


def _draw_logo(c, school, x, y, size) -> None:
    for logo in (school["logo_path"], BUNDLED_LOGO):
        if not logo or not Path(logo).is_file():
            continue
        try:
            c.drawImage(
                _logo_reader(Path(logo)),
                x,
                y,
                width=size,
                height=size,
                preserveAspectRatio=True,
                mask="auto",
            )
        except Exception:
            # e.g. an uploaded SVG/WebP ReportLab can't read: try the next one.
            logger.warning("Could not draw receipt logo %s", logo)
            continue
        return
    _draw_mark(c, x, y, size)


PAGE_BG = HexColor("#faf8f3")
HEADER_DARK = HexColor("#0a3528")
HEADER_LIGHT = HexColor("#145a43")
GOLD_DEEP = HexColor("#b08a3e")
GOLD_LIGHT = HexColor("#e6cd8a")
CARD_BG = HexColor("#f3f8f5")
ICON_BG = HexColor("#e2efe7")
LABEL_BG = HexColor("#f6f0e3")
TABLE_BORDER = HexColor("#d9d2c2")
ROW_LINE = HexColor("#e9e4d8")
FEE_BG = HexColor("#e6f0ea")
CODE_BG = HexColor("#eceeec")
DARK_TEXT = HexColor("#16241d")

# status: (pill fill, pill border, text, icon)
STATUS_PILLS = {
    "pending": (HexColor("#fde38f"), HexColor("#f2cf63"), DARK_TEXT, "clock"),
    "approved": (HexColor("#d7eedf"), HexColor("#b5dcc3"), HexColor("#0f5132"), "check"),
    "rejected": (HexColor("#f8d9dc"), HexColor("#efb9bf"), HexColor("#842029"), "cross"),
}

# Rows exactly as on the receipt design; values are the application's data.
ROW_LABELS = {
    "student_name": "Student Name",
    "student_name_bn": "নামের বাংলা",
    "guardian_name": "Guardian Name",
    "applying_class": "Applying Class",
    "mobile": "Mobile",
    "email": "Email",
    "fee": "Admission Fee",
    "method": "Payment Method",
    "transaction_id": "Transaction ID",
    "submitted": "Submission Date",
    "status": "Application Status",
    "rejection_reason": "Rejection Reason",
}


def _top(height, t_mm):
    """Converts a distance from the top of the page (mm) to a PDF y."""
    return height - t_mm * mm


def _fit_size(text, font, size, max_width, minimum):
    while size > minimum and _word_width(text, font, _bengali_counterpart(font), size) > max_width:
        size -= 0.5
    return size


def _draw_fitted(c, x, y, text, font, size):
    # Draws a single line that may mix Latin and Bengali (school names).
    bengali_font = _bengali_counterpart(font)
    space = pdfmetrics.stringWidth(" ", font, size)
    for i, word in enumerate(text.split()):
        if i:
            x += space
        x += _draw_word(c, x, y, word, font, bengali_font, size)


def _star_path(c, cx, cy, r):
    inner = r * 0.42
    p = c.beginPath()
    for k in range(8):
        angle = math.pi / 2 + k * math.pi / 4
        radius = r if k % 2 == 0 else inner
        px, py = cx + radius * math.cos(angle), cy + radius * math.sin(angle)
        if k == 0:
            p.moveTo(px, py)
        else:
            p.lineTo(px, py)
    p.close()
    return p


def _arch_outline(c, height, closed):
    """The mihrab-style arch in the header's right corner (mm from top)."""
    pt = lambda x, t: (x * mm, _top(height, t))
    p = c.beginPath()
    p.moveTo(*pt(181, 44))
    p.lineTo(*pt(181, 33))
    p.curveTo(*pt(181, 28.5), *pt(183.5, 26.5), *pt(186.5, 25.5))
    p.curveTo(*pt(189.5, 24.5), *pt(190.5, 21.5), *pt(191.5, 19))
    p.curveTo(*pt(193, 15), *pt(196, 13), *pt(199, 12.2))
    p.curveTo(*pt(202, 11.4), *pt(203.5, 8), *pt(204.5, 4))
    p.curveTo(*pt(205.5, 7), *pt(207.5, 8.5), *pt(211, 9))
    if closed:
        p.lineTo(*pt(211, 44))
        p.close()
    return p


def _draw_header(c, school, width, height):
    band_h = 44 * mm
    band_bottom = height - band_h

    # Deep green, lighter toward the right.
    c.saveState()
    clip = c.beginPath()
    clip.rect(0, band_bottom, width, band_h)
    c.clipPath(clip, stroke=0, fill=0)
    c.linearGradient(0, band_bottom, width, height, (HEADER_DARK, HEADER_LIGHT), extend=True)
    c.restoreState()

    # Arch: a slightly lighter panel with a faint star lattice, gold edge.
    c.saveState()
    arch = _arch_outline(c, height, closed=True)
    c.clipPath(arch, stroke=0, fill=0)
    c.setFillColor(HexColor("#1b6a50"))
    c.setFillAlpha(0.55)
    c.rect(170 * mm, band_bottom, 45 * mm, band_h, fill=1, stroke=0)
    c.setFillAlpha(1)
    c.setStrokeColor(GOLD)
    c.setStrokeAlpha(0.22)
    c.setLineWidth(0.4)
    step = 7 * mm
    row = 0
    y = band_bottom + step / 2
    while y < height + step:
        x = 178 * mm + (step / 2 if row % 2 else 0)
        while x < width + step:
            c.drawPath(_star_path(c, x, y, step * 0.42), stroke=1, fill=0)
            x += step
        y += step
        row += 1
    c.restoreState()
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.6)
    c.drawPath(_arch_outline(c, height, closed=False), stroke=1, fill=0)

    # Gold rule along the bottom of the band.
    rule_h = 1.6 * mm
    c.saveState()
    clip = c.beginPath()
    clip.rect(0, band_bottom - rule_h, width, rule_h)
    c.clipPath(clip, stroke=0, fill=0)
    c.linearGradient(
        0, band_bottom, width, band_bottom,
        (GOLD_DEEP, GOLD_LIGHT, GOLD, GOLD_LIGHT, GOLD_DEEP),
        positions=(0, 0.25, 0.5, 0.75, 1), extend=True,
    )
    c.restoreState()

    # Crest, divider, then the eyebrow / English name / Bengali name block.
    crest = 31 * mm
    crest_x = 15 * mm
    crest_y = band_bottom + (band_h - crest) / 2
    _draw_logo(c, school, crest_x, crest_y, crest)
    divider_x = crest_x + crest + 7 * mm
    c.setStrokeColor(GOLD_SOFT)
    c.setStrokeAlpha(0.8)
    c.setLineWidth(0.8)
    c.line(divider_x, _top(height, 11.5), divider_x, _top(height, 33))
    c.setStrokeAlpha(1)

    text_x = divider_x + 7 * mm
    max_w = 178 * mm - text_x
    c.setFillColor(GOLD)
    c.setFont(LATIN_SEMIBOLD, 8.5)
    c.drawString(text_x, _top(height, 13), "IDEAL GLOBAL QUR'ANIC SCHOOL", charSpace=1.5)
    name = school["name"]
    name_size = _fit_size(name, LATIN_BOLD, 21, max_w, 14)
    c.setFillColor(white)
    _draw_fitted(c, text_x, _top(height, 23.5), name, LATIN_BOLD, name_size)
    if school["name_bn"]:
        bn_size = _fit_size(school["name_bn"], BENGALI_BOLD, 17, max_w, 12)
        _draw_text(c, text_x, _top(height, 34), school["name_bn"], BENGALI_BOLD, bn_size)
    return band_bottom - rule_h


def _draw_book(c, cx, base_y, w, h, color, line_width, alpha=1.0):
    """Open book outline: two curved pages meeting at a spine."""
    c.saveState()
    c.setStrokeColor(color)
    c.setStrokeAlpha(alpha)
    c.setLineWidth(line_width)
    c.setLineJoin(1)
    c.setLineCap(1)
    half = w / 2
    for side in (-1, 1):
        p = c.beginPath()
        p.moveTo(cx, base_y)
        p.curveTo(cx + side * half * 0.3, base_y + h * 0.2, cx + side * half * 0.7, base_y + h * 0.22, cx + side * half, base_y + h * 0.12)
        p.lineTo(cx + side * half, base_y + h * 0.86)
        p.curveTo(cx + side * half * 0.7, base_y + h * 1.0, cx + side * half * 0.28, base_y + h * 0.98, cx, base_y + h * 0.74)
        c.drawPath(p, stroke=1, fill=0)
        # page lines
        for k in (0.3, 0.48, 0.66):
            q = c.beginPath()
            q.moveTo(cx + side * half * 0.18, base_y + h * (k + 0.1))
            q.curveTo(cx + side * half * 0.4, base_y + h * (k + 0.17), cx + side * half * 0.62, base_y + h * (k + 0.17), cx + side * half * 0.82, base_y + h * (k + 0.12))
            c.drawPath(q, stroke=1, fill=0)
        # outer cover edge
        e = c.beginPath()
        e.moveTo(cx, base_y - h * 0.08)
        e.curveTo(cx + side * half * 0.4, base_y + h * 0.1, cx + side * half * 0.8, base_y + h * 0.1, cx + side * half * 1.1, base_y + h * 0.02)
        e.lineTo(cx + side * half * 1.1, base_y + h * 0.74)
        c.drawPath(e, stroke=1, fill=0)
    c.line(cx, base_y - h * 0.08, cx, base_y + h * 0.75)
    c.restoreState()


def _draw_title(c, width, height, top_mm):
    _draw_book(c, width / 2, _top(height, top_mm + 9), 17 * mm, 8.5 * mm, GOLD, 1.1)
    title = "Admission Application Receipt"
    size = 21
    baseline = _top(height, top_mm + 19)
    c.setFillColor(FOREST)
    c.setFont(SERIF_BOLD, size)
    c.drawCentredString(width / 2, baseline, title)
    title_w = pdfmetrics.stringWidth(title, SERIF_BOLD, size)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.9)
    mid = baseline + size * 0.3
    gap, length = 6 * mm, 19 * mm
    left_end = width / 2 - title_w / 2 - gap
    right_start = width / 2 + title_w / 2 + gap
    c.line(left_end - length, mid, left_end, mid)
    c.line(right_start, mid, right_start + length, mid)
    return top_mm + 19


def _draw_doc_icon(c, x, y, size, color):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.1)
    c.setLineJoin(1)
    c.setLineCap(1)
    w, h = size * 0.62, size * 0.8
    left, bottom = x + (size - w) / 2, y + (size - h) / 2
    fold = w * 0.32
    p = c.beginPath()
    p.moveTo(left, bottom)
    p.lineTo(left, bottom + h)
    p.lineTo(left + w - fold, bottom + h)
    p.lineTo(left + w, bottom + h - fold)
    p.lineTo(left + w, bottom)
    p.close()
    c.drawPath(p, stroke=1, fill=0)
    f = c.beginPath()
    f.moveTo(left + w - fold, bottom + h)
    f.lineTo(left + w - fold, bottom + h - fold)
    f.lineTo(left + w, bottom + h - fold)
    c.drawPath(f, stroke=1, fill=0)
    for k, frac in ((0.45, 0.62), (0.28, 0.45)):
        c.line(left + w * 0.22, bottom + h * k, left + w * (0.22 + frac), bottom + h * k)
    c.restoreState()


def _draw_id_card(c, application, width, height, top_mm):
    card_w, card_h = 134 * mm, 17 * mm
    x = (width - card_w) / 2
    bottom = _top(height, top_mm + 17)
    c.setFillColor(CARD_BG)
    c.setStrokeColor(FOREST)
    c.setLineWidth(0.9)
    c.roundRect(x, bottom, card_w, card_h, 3 * mm, fill=1, stroke=1)

    icon = 10 * mm
    icon_x = x + 7 * mm
    icon_y = bottom + (card_h - icon) / 2
    c.setFillColor(ICON_BG)
    c.roundRect(icon_x, icon_y, icon, icon, 2 * mm, fill=1, stroke=0)
    _draw_doc_icon(c, icon_x, icon_y, icon, FOREST)

    mid_y = bottom + card_h / 2
    c.setFillColor(DARK_TEXT)
    c.setFont(LATIN_SEMIBOLD, 13.5)
    c.drawString(icon_x + icon + 6 * mm, mid_y - 13.5 * 0.35, "Application ID")
    divider_x = x + 66 * mm
    c.setStrokeColor(TABLE_BORDER)
    c.setLineWidth(0.8)
    c.line(divider_x, bottom + 4.5 * mm, divider_x, bottom + card_h - 4.5 * mm)

    value = application.application_id
    value_x = divider_x + 9 * mm
    size = _fit_size(value, LATIN_BOLD, 24, x + card_w - 6 * mm - value_x, 12)
    c.setFillColor(FOREST)
    c.setFont(LATIN_BOLD, size)
    c.drawString(value_x, mid_y - size * 0.36, value)

    # New applications share one number for both IDs. Older ones have a
    # separate receipt number; keep it on the receipt, quietly.
    if application.receipt_id and application.receipt_id != application.application_id:
        c.setFillColor(MUTED)
        c.setFont(LATIN_MEDIUM, 8.5)
        c.drawCentredString(width / 2, bottom - 4.5 * mm, f"Receipt ID  {application.receipt_id}")
        return top_mm + 22
    return top_mm + 17


def _draw_section_tab(c, width, height, top_mm, margin):
    tab_w, tab_h, slant = 72 * mm, 10.5 * mm, 6 * mm
    bottom = _top(height, top_mm + 10.5)
    x = margin - 1 * mm
    p = c.beginPath()
    p.moveTo(x + 1.6 * mm, bottom)
    p.lineTo(x + tab_w - slant, bottom)
    p.lineTo(x + tab_w, bottom + tab_h)
    p.lineTo(x + 1.6 * mm, bottom + tab_h)
    p.curveTo(x, bottom + tab_h, x, bottom + tab_h, x, bottom + tab_h - 1.6 * mm)
    p.lineTo(x, bottom + 1.6 * mm)
    p.curveTo(x, bottom, x, bottom, x + 1.6 * mm, bottom)
    p.close()
    c.saveState()
    c.clipPath(p, stroke=0, fill=0)
    c.linearGradient(x, bottom, x + tab_w, bottom, (HEADER_DARK, HEADER_LIGHT), extend=True)
    c.restoreState()
    stripe = c.beginPath()
    stripe.moveTo(x + tab_w - slant + 0.4 * mm, bottom)
    stripe.lineTo(x + tab_w - slant + 3.2 * mm, bottom)
    stripe.lineTo(x + tab_w + 3.2 * mm, bottom + tab_h)
    stripe.lineTo(x + tab_w + 0.4 * mm, bottom + tab_h)
    stripe.close()
    c.setFillColor(GOLD)
    c.drawPath(stripe, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#1a5c45"))
    c.setLineWidth(1.4)
    line_y = bottom + 1.8 * mm
    c.line(x + tab_w + 2 * mm, line_y, width - margin, line_y)
    c.setFillColor(white)
    c.setFont(LATIN_BOLD, 14)
    c.drawString(x + 6 * mm, bottom + tab_h / 2 - 14 * 0.35, "Application Details")
    return top_mm + 10.5


def _draw_status_icon(c, kind, cx, cy, r, color):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.2)
    c.setLineCap(1)
    c.setLineJoin(1)
    if kind == "clock":
        c.circle(cx, cy, r, stroke=1, fill=0)
        c.line(cx, cy, cx, cy + r * 0.62)
        c.line(cx, cy, cx + r * 0.48, cy - r * 0.3)
    elif kind == "check":
        c.circle(cx, cy, r, stroke=1, fill=0)
        p = c.beginPath()
        p.moveTo(cx - r * 0.45, cy)
        p.lineTo(cx - r * 0.1, cy - r * 0.38)
        p.lineTo(cx + r * 0.5, cy + r * 0.35)
        c.drawPath(p, stroke=1, fill=0)
    else:
        c.circle(cx, cy, r, stroke=1, fill=0)
        c.line(cx - r * 0.38, cy - r * 0.38, cx + r * 0.38, cy + r * 0.38)
        c.line(cx - r * 0.38, cy + r * 0.38, cx + r * 0.38, cy - r * 0.38)
    c.restoreState()


def _row_specs(application, submitted, value_w):
    """(key, label, value, kind, lines, size, height) for each row shown."""
    values = [
        ("student_name", application.student_name, "text"),
        ("student_name_bn", application.student_name_bn, "text"),
        ("guardian_name", application.guardian_name, "text"),
        ("applying_class", application.applying_class, "text"),
        ("mobile", application.mobile, "text"),
        ("email", application.email, "text"),
        ("fee", f"BDT {int(application.payment_amount):,}", "fee"),
        ("method", application.payment_method_label(), "text"),
        ("transaction_id", application.transaction_id, "code"),
        ("submitted", submitted.strftime("%d %B %Y, %I:%M %p"), "text"),
        ("status", application.get_status_display(), "status"),
    ]
    if application.rejection_reason:
        values.append(("rejection_reason", application.rejection_reason, "text"))
    specs = []
    for key, value, kind in values:
        if not value:
            continue
        value = str(value)
        if kind == "fee":
            font, size = LATIN_BOLD, 15
        elif kind == "code":
            font, size = MONO, 12
        elif kind == "status":
            font, size = LATIN_BOLD, 12
        else:
            # Inter; Bengali runs inside switch to Noto Sans Bengali.
            font, size = LATIN, 12
        lines = [[value]] if kind in ("status", "code") else _wrap(value, font, size, value_w)
        leading = _leading(value, size)
        base_h = {"status": 13.5 * mm, "fee": 11.5 * mm}.get(kind, 10.6 * mm)
        row_h = max(base_h, (len(lines) - 1) * leading + 10.6 * mm)
        specs.append((key, ROW_LABELS[key], value, kind, lines, font, size, leading, row_h))
    return specs


def _draw_table(c, specs, left, top_y, table_w, label_w, application):
    total_h = sum(spec[-1] for spec in specs)
    bottom = top_y - total_h
    radius = 2.5 * mm
    frame = c.beginPath()
    frame.roundRect(left, bottom, table_w, total_h, radius)
    c.saveState()
    c.clipPath(frame, stroke=0, fill=0)
    c.setFillColor(white)
    c.rect(left, bottom, table_w, total_h, fill=1, stroke=0)
    c.setFillColor(LABEL_BG)
    c.rect(left, bottom, label_w, total_h, fill=1, stroke=0)
    y = top_y
    for key, label, value, kind, lines, font, size, leading, row_h in specs:
        if kind == "fee":
            c.setFillColor(FEE_BG)
            c.rect(left + label_w, y - row_h, table_w - label_w, row_h, fill=1, stroke=0)
        y -= row_h
    c.restoreState()

    y = top_y
    value_x = left + label_w + 7 * mm
    for index, (key, label, value, kind, lines, font, size, leading, row_h) in enumerate(specs):
        row_top = y
        row_mid = row_top - row_h / 2
        single = len(lines) == 1
        first_baseline = (row_mid - size * 0.35) if single else (row_top - 4.6 * mm - size * 0.35)
        label_baseline = (row_mid - 11.5 * 0.35) if single else first_baseline

        c.setFillColor(DARK_TEXT)
        _draw_fitted(c, left + 8 * mm, label_baseline, label, LATIN_MEDIUM, 11.5)

        if kind == "status":
            fill, border, ink, icon = STATUS_PILLS.get(application.status, STATUS_PILLS["pending"])
            text_w = pdfmetrics.stringWidth(value, LATIN_BOLD, size)
            pill_h = 8.6 * mm
            icon_r = 2 * mm
            pill_w = 4 * mm + icon_r * 2 + 2.6 * mm + text_w + 4.5 * mm
            pill_y = row_mid - pill_h / 2
            c.setFillColor(fill)
            c.setStrokeColor(border)
            c.setLineWidth(0.6)
            c.roundRect(value_x, pill_y, pill_w, pill_h, 2 * mm, fill=1, stroke=1)
            _draw_status_icon(c, icon, value_x + 4 * mm + icon_r, row_mid, icon_r, ink)
            c.setFillColor(ink)
            c.setFont(LATIN_BOLD, size)
            c.drawString(value_x + 4 * mm + icon_r * 2 + 2.6 * mm, row_mid - size * 0.35, value)
        elif kind == "code":
            text_w = pdfmetrics.stringWidth(value, MONO, size)
            max_w = table_w - label_w - 12 * mm
            size_fit = size
            while text_w > max_w - 8 * mm and size_fit > 8:
                size_fit -= 0.5
                text_w = pdfmetrics.stringWidth(value, MONO, size_fit)
            pill_h = 7.4 * mm
            c.setFillColor(CODE_BG)
            c.roundRect(value_x, row_mid - pill_h / 2, text_w + 8 * mm, pill_h, 1.8 * mm, fill=1, stroke=0)
            c.setFillColor(DARK_TEXT)
            c.setFont(MONO, size_fit)
            c.drawString(value_x + 4 * mm, row_mid - size_fit * 0.36, value, charSpace=0.4)
        else:
            c.setFillColor(FOREST if kind == "fee" else DARK_TEXT)
            _draw_lines(c, lines, value_x, first_baseline, font, size, leading)

        y -= row_h
        if index < len(specs) - 1:
            c.setStrokeColor(ROW_LINE)
            c.setLineWidth(0.6)
            c.line(left, y, left + table_w, y)

    c.setStrokeColor(TABLE_BORDER)
    c.setLineWidth(0.8)
    c.roundRect(left, bottom, table_w, total_h, radius, fill=0, stroke=1)
    return bottom


def _draw_page_base(c, width, height):
    c.setFillColor(PAGE_BG)
    c.rect(0, 0, width, height, fill=1, stroke=0)


def _draw_footer(c, width):
    band_h = 5 * mm
    c.setFillColor(FOREST)
    c.rect(0, 0, width, band_h, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, band_h, width, 0.9 * mm, fill=1, stroke=0)

    text = "This receipt acknowledges the successful submission of the admission application."
    size = 10.5
    baseline = 18 * mm
    c.setFillColor(DARK_TEXT)
    c.setFont(SERIF_ITALIC, size)
    c.drawCentredString(width / 2, baseline, text)
    text_w = pdfmetrics.stringWidth(text, SERIF_ITALIC, size)
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.8)
    mid = baseline + size * 0.3
    gap = 7 * mm
    c.line(13 * mm, mid, width / 2 - text_w / 2 - gap, mid)
    c.line(width / 2 + text_w / 2 + gap, mid, width - 13 * mm, mid)


def build_receipt_pdf(application) -> bytes:
    _register_fonts()
    school = school_info()
    submitted = timezone.localtime(application.created_at)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    c.setTitle(f"Admission receipt {application.receipt_id}")
    c.setAuthor(school["name"])
    width, height = A4
    margin = 12 * mm

    _draw_page_base(c, width, height)
    _draw_header(c, school, width, height)
    t = _draw_title(c, width, height, 50)
    t = _draw_id_card(c, application, width, height, t + 8)
    t = _draw_section_tab(c, width, height, t + 11, margin)

    table_left = margin
    table_w = width - 2 * margin
    label_w = 60 * mm
    specs = _row_specs(application, submitted, table_w - label_w - 14 * mm)

    # Rows never split; a very long rejection reason moves to a new page.
    floor = 30 * mm
    top_y = _top(height, t + 4)
    page_rows = []
    for spec in specs:
        used = sum(row[-1] for row in page_rows)
        if page_rows and top_y - used - spec[-1] < floor:
            _draw_table(c, page_rows, table_left, top_y, table_w, label_w, application)
            c.showPage()
            _draw_page_base(c, width, height)
            top_y = height - 18 * mm
            page_rows = []
        page_rows.append(spec)
    table_bottom = _draw_table(c, page_rows, table_left, top_y, table_w, label_w, application)

    # Faint open book in the lower right, partly over the table's corner.
    _draw_book(c, width - 36 * mm, max(table_bottom - 8 * mm, 34 * mm), 42 * mm, 24 * mm, GOLD, 1.3, alpha=0.11)
    _draw_footer(c, width)

    c.showPage()
    c.save()
    return buffer.getvalue()


def generate_receipt_pdf(application, *, force: bool = False) -> None:
    if application.receipt_pdf and not force:
        return
    if force and application.receipt_pdf:
        application.receipt_pdf.delete(save=False)
    pdf_bytes = build_receipt_pdf(application)
    application.receipt_pdf.save(
        f"{application.receipt_id}.pdf",
        ContentFile(pdf_bytes),
        save=True,
    )


def send_receipt_email(application) -> bool:
    if not application.email:
        return False
    generate_receipt_pdf(application)
    application.refresh_from_db(fields=["receipt_pdf", "receipt_email_sent"])
    if not application.receipt_pdf:
        return False

    school = school_info()
    submitted = timezone.localtime(application.created_at).strftime("%d %B %Y, %I:%M %p")
    body = (
        f"Assalamu Alaikum,\n\n"
        f"Your admission application to {school['name']} has been received.\n\n"
        f"Application confirmation\n"
        f"Application ID: {application.application_id}\n"
        f"Receipt ID: {application.receipt_id}\n"
        f"Submitted: {submitted}\n"
        f"Status: {application.get_status_display()}\n\n"
        f"Application information\n"
        f"Student: {application.student_name}\n"
        f"Guardian: {application.guardian_name}\n"
        f"Applying class: {application.applying_class}\n"
        f"Mobile: {application.mobile}\n"
        f"Email: {application.email}\n\n"
        f"Payment information\n"
        f"Admission fee: BDT {int(application.payment_amount):,}\n"
        f"Payment method: {application.payment_method_label()}\n"
        f"Transaction ID: {application.transaction_id}\n"
        f"Payment date: {application.payment_date}\n\n"
        f"The official PDF receipt is attached. Please keep it for future reference.\n\n"
        f"{school['name']}\n"
        f"{school['address']}\n"
        f"{school['phones']}\n"
        f"{school['email']}\n"
    )
    message = EmailMessage(
        subject="IGQS Admission Application Receipt",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[application.email],
    )
    with application.receipt_pdf.open("rb") as pdf_file:
        message.attach(
            f"{application.receipt_id}.pdf",
            pdf_file.read(),
            "application/pdf",
        )
    message.send()
    application.receipt_email_sent = True
    application.save(update_fields=["receipt_email_sent"])
    return True


def send_status_email(application) -> bool:
    if not application.email:
        return False
    generate_receipt_pdf(application)
    application.refresh_from_db(fields=["receipt_pdf", "status", "rejection_reason"])
    school = school_info()
    status_label = application.get_status_display()
    reason = (
        f"\nRejection reason: {application.rejection_reason}\n"
        if application.rejection_reason
        else "\n"
    )
    body = (
        f"Assalamu Alaikum,\n\n"
        f"The status of your admission application to {school['name']} has been updated.\n\n"
        f"Application ID: {application.application_id}\n"
        f"Receipt ID: {application.receipt_id}\n"
        f"Status: {status_label}\n"
        f"{reason}"
        f"You can check this status again with your Application ID or Receipt ID.\n"
        f"An updated PDF receipt is attached.\n\n"
        f"{school['name']}\n"
        f"{school['address']}\n"
        f"{school['phones']}\n"
        f"{school['email']}\n"
    )
    message = EmailMessage(
        subject=f"IGQS Admission Application {status_label}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[application.email],
    )
    if application.receipt_pdf:
        with application.receipt_pdf.open("rb") as pdf_file:
            message.attach(
                f"{application.receipt_id}.pdf",
                pdf_file.read(),
                "application/pdf",
            )
    message.send()
    return True


def notify_staff_new_application(application) -> bool:
    recipient = (getattr(settings, "STAFF_NOTIFICATION_EMAIL", "") or "").strip()
    if not recipient:
        return False
    school = school_info()
    submitted = timezone.localtime(application.created_at).strftime("%d %B %Y, %I:%M %p")
    body = (
        f"A new admission payment is waiting for verification.\n\n"
        f"Application ID: {application.application_id}\n"
        f"Receipt ID: {application.receipt_id}\n"
        f"Submitted: {submitted}\n"
        f"Status: {application.get_status_display()}\n\n"
        f"Student: {application.student_name}\n"
        f"Class: {application.applying_class}\n"
        f"Guardian: {application.guardian_name}\n"
        f"Phone: {application.mobile}\n"
        f"Email: {application.email}\n\n"
        f"Payment method: {application.payment_method_label()}\n"
        f"Amount: BDT {int(application.payment_amount):,}\n"
        f"Transaction ID: {application.transaction_id}\n"
        f"Payment date: {application.payment_date}\n\n"
        f"{school['name']}\n"
    )
    message = EmailMessage(
        subject=f"IGQS new admission payment {application.application_id}",
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    try:
        if application.receipt_pdf:
            with application.receipt_pdf.open("rb") as pdf_file:
                message.attach(
                    f"{application.receipt_id}.pdf",
                    pdf_file.read(),
                    "application/pdf",
                )
        message.send()
        return True
    except Exception:
        logger.exception(
            "Failed to notify staff about admission %s",
            application.application_id,
        )
        return False


def issue_receipt(application, *, send_email: bool = False) -> None:
    generate_receipt_pdf(application)
    if send_email and not application.receipt_email_sent:
        try:
            send_receipt_email(application)
        except Exception:
            logger.exception(
                "Failed to email admission receipt %s to %s",
                application.receipt_id,
                application.email,
            )


def refresh_application_after_review(application) -> None:
    try:
        generate_receipt_pdf(application, force=True)
    except Exception:
        logger.exception("Failed to regenerate receipt PDF for %s", application.application_id)
    try:
        send_status_email(application)
    except Exception:
        logger.exception(
            "Failed to email admission status %s to %s",
            application.application_id,
            application.email,
        )
