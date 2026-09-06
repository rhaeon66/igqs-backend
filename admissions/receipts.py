import logging
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils import timezone
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from content.models import SiteSettings

logger = logging.getLogger(__name__)

FOREST = HexColor("#0f3d30")
GOLD = HexColor("#c4a35a")
INK = HexColor("#1c241f")
MUTED = HexColor("#5c6b66")
CREAM = HexColor("#f7f1e3")
RULE = HexColor("#e4d5b3")

_FONTS_READY = False
LATIN = "IGQSSans"
LATIN_BOLD = "IGQSSans-Bold"
BENGALI = "IGQSBengali"

NOTO_DIR = Path("/usr/share/fonts/truetype/noto")


def _register_fonts() -> None:
    global _FONTS_READY
    if _FONTS_READY:
        return
    pdfmetrics.registerFont(TTFont(LATIN, str(NOTO_DIR / "NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(LATIN_BOLD, str(NOTO_DIR / "NotoSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont(BENGALI, str(NOTO_DIR / "NotoSansBengali-Regular.ttf")))
    _FONTS_READY = True


def _has_bengali(text: str) -> bool:
    return any("\u0980" <= char <= "\u09ff" for char in text)


def _font_for(text: str, bold: bool = False) -> str:
    if _has_bengali(text):
        return BENGALI
    return LATIN_BOLD if bold else LATIN


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


def _draw_wrapped(c, text, x, y, max_width, font, size, color=INK, leading=None):
    leading = leading or size + 4
    c.setFont(font, size)
    c.setFillColor(color)
    words = text.split()
    if not words:
        return y
    lines = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if pdfmetrics.stringWidth(trial, font, size) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    for i, line in enumerate(lines):
        c.drawString(x, y - i * leading, line)
    return y - (len(lines) - 1) * leading


def build_receipt_pdf(application) -> bytes:
    _register_fonts()
    school = school_info()
    submitted = timezone.localtime(application.created_at)
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    margin = 18 * mm

    c.setFillColor(FOREST)
    c.rect(0, height - 48 * mm, width, 48 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.rect(0, height - 50 * mm, width, 2.2 * mm, fill=1, stroke=0)

    mark_size = 22 * mm
    mark_x = margin
    mark_y = height - 40 * mm
    if school["logo_path"] and Path(school["logo_path"]).exists():
        c.drawImage(
            school["logo_path"],
            mark_x,
            mark_y,
            width=mark_size,
            height=mark_size,
            preserveAspectRatio=True,
            mask="auto",
        )
    else:
        _draw_mark(c, mark_x, mark_y, mark_size)

    text_x = mark_x + mark_size + 8 * mm
    c.setFillColor(GOLD)
    c.setFont(LATIN, 8)
    c.drawString(text_x, height - 18 * mm, "IDEAL GLOBAL QUR'ANIC SCHOOL")
    c.setFillColor(white)
    c.setFont(LATIN_BOLD, 16)
    c.drawString(text_x, height - 26 * mm, school["name"])
    if school["name_bn"]:
        c.setFont(BENGALI, 10)
        c.drawString(text_x, height - 32 * mm, school["name_bn"])
    c.setFont(LATIN, 10)
    c.setFillColor(GOLD)
    c.drawString(text_x, height - 40 * mm, "Admission Application Receipt")

    y = height - 66 * mm
    box_w = (width - 2 * margin - 6 * mm) / 2
    for i, (label, value) in enumerate(
        (
            ("Receipt ID", application.receipt_id),
            ("Application ID", application.application_id),
        )
    ):
        x = margin + i * (box_w + 6 * mm)
        c.setFillColor(CREAM)
        c.roundRect(x, y - 4 * mm, box_w, 16 * mm, 4, fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.setFont(LATIN, 8)
        c.drawString(x + 4 * mm, y + 7 * mm, label.upper())
        c.setFillColor(FOREST)
        c.setFont(LATIN_BOLD, 12)
        c.drawString(x + 4 * mm, y + 1 * mm, value)

    y -= 18 * mm
    rows = [
        ("Student name", application.student_name),
        ("Name in Bengali", application.student_name_bn),
        ("Guardian name", application.guardian_name),
        ("Applying class", application.applying_class),
        ("Mobile", application.mobile),
        ("Email", application.email),
        ("Admission fee", f"BDT {int(application.payment_amount):,}"),
        ("Payment method", application.get_payment_method_display()),
        ("Transaction ID", application.transaction_id),
        ("Submission date", submitted.strftime("%d %B %Y, %I:%M %p")),
        ("Application status", application.get_status_display()),
    ]
    if application.rejection_reason:
        rows.append(("Rejection reason", application.rejection_reason))

    c.setFont(LATIN_BOLD, 11)
    c.setFillColor(FOREST)
    c.drawString(margin, y, "Application details")
    y -= 3 * mm
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(margin, y, width - margin, y)
    y -= 8 * mm

    label_w = 48 * mm
    value_x = margin + label_w
    value_w = width - margin - value_x
    for label, value in rows:
        if not value:
            continue
        c.setFillColor(GOLD)
        c.setFont(LATIN, 8)
        c.drawString(margin, y, label.upper())
        font = _font_for(str(value))
        y = _draw_wrapped(c, str(value), value_x, y, value_w, font, 10)
        y -= 8 * mm

    info_top = 52 * mm
    c.setFillColor(CREAM)
    c.roundRect(margin, 20 * mm, width - 2 * margin, 32 * mm, 4, fill=1, stroke=0)
    info_y = info_top - 6 * mm
    c.setFillColor(FOREST)
    c.setFont(LATIN_BOLD, 10)
    c.drawString(margin + 5 * mm, info_y, "Official school information")
    info_y -= 6 * mm
    c.setFont(LATIN, 8)
    c.setFillColor(INK)
    official = "  ·  ".join(
        part for part in (school["name"], school["address"], school["phones"], school["email"]) if part
    )
    _draw_wrapped(
        c,
        official,
        margin + 5 * mm,
        info_y,
        width - 2 * margin - 10 * mm,
        LATIN,
        8,
        MUTED,
        leading=11,
    )

    c.setFillColor(FOREST)
    c.rect(0, 0, width, 16 * mm, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont(LATIN, 8)
    c.drawCentredString(
        width / 2,
        7 * mm,
        "This is a computer-generated receipt for your admission application. Keep it for future reference.",
    )

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
        f"Payment method: {application.get_payment_method_display()}\n"
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
