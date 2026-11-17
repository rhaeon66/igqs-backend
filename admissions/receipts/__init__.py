from admissions.receipts import pdf as _pdf
from admissions.receipts.mail import (
    issue_receipt,
    notify_staff_new_application,
    refresh_application_after_review,
    send_receipt_email,
    send_status_email,
)
from admissions.receipts.pdf import (
    _logo_reader,
    _prepare,
    _register_fonts,
    build_receipt_pdf,
    generate_receipt_pdf,
    school_info,
)


def __getattr__(name):
    # Font names are rebound inside pdf.py after registration. A normal import
    # would freeze the fallback face, so attribute lookup stays live.
    return getattr(_pdf, name)
