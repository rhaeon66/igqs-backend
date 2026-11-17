from django.conf import settings
from django.core.mail import EmailMessage
from django.utils import timezone

from admissions.receipts.pdf import generate_receipt_pdf, logger, school_info


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
