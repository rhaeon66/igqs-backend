import re

from django.http import FileResponse
from rest_framework import status
from rest_framework.response import Response

from admissions.models import AdmissionApplication, ApplicationStatus
from admissions.receipts import issue_receipt


_LEGACY_RECEIPT = re.compile(r"^IGQS-RC-0*(\d+)$", re.IGNORECASE)
_LEGACY_APPLICATION = re.compile(r"^IGQS-\d{4}-0*(\d+)$", re.IGNORECASE)


def normalize_receipt_id(value: str) -> str:
    text = (value or "").strip().upper().replace(" ", "")
    for pattern in (_LEGACY_RECEIPT, _LEGACY_APPLICATION):
        match = pattern.fullmatch(text)
        if match:
            return str(int(match.group(1)))
    if text.isdigit():
        return str(int(text))
    return text


def _candidate_ids(value: str) -> list[str]:
    # Rows created before IDs became numeric still store "IGQS-RC-00001",
    # so try the value as given before its normalized (numeric) form.
    raw = (value or "").strip().replace(" ", "")
    normalized = normalize_receipt_id(value)
    return [v for v in dict.fromkeys([raw, normalized]) if v]


def find_application_by_receipt(receipt_id: str):
    for rid in _candidate_ids(receipt_id):
        application = AdmissionApplication.objects.filter(receipt_id__iexact=rid).first()
        if application:
            return application
    return None


def find_application_by_query(value: str):
    for query in _candidate_ids(value):
        application = AdmissionApplication.objects.filter(application_id__iexact=query).first()
        if application:
            return application
    return find_application_by_receipt(value)


def receipt_pdf_response(application, request, *, public=False):
    # Guardians only get the PDF after staff approve the payment. Staff
    # endpoints call this with public=False so they can still review pending
    # applications.
    if public and application.status != ApplicationStatus.APPROVED:
        return Response(
            {"detail": "Receipt is available after payment is approved."},
            status=status.HTTP_403_FORBIDDEN,
        )
    issue_receipt(application, send_email=False)
    application.refresh_from_db()
    if not application.receipt_pdf:
        return Response(
            {"detail": "Receipt is not available yet."},
            status=status.HTTP_404_NOT_FOUND,
        )
    inline = request.query_params.get("inline") == "1"
    return FileResponse(
        application.receipt_pdf.open("rb"),
        as_attachment=not inline,
        filename=f"{application.receipt_id}.pdf",
        content_type="application/pdf",
    )


def application_payload(application, request):
    transaction = application.transaction_data()
    screenshot = transaction["payment_screenshot"]
    if screenshot and request:
        transaction["payment_screenshot"] = request.build_absolute_uri(screenshot)
    receipt_url = ""
    receipt_view_url = ""
    if (
        request
        and application.receipt_id
        and application.status == ApplicationStatus.APPROVED
    ):
        receipt_url = request.build_absolute_uri(
            f"/api/admissions/receipts/{application.receipt_id}/pdf/"
        )
        receipt_view_url = request.build_absolute_uri(
            f"/api/admissions/receipts/{application.receipt_id}/pdf/?inline=1"
        )
    return {
        "application_id": application.application_id,
        "receipt_id": application.receipt_id,
        "student_name": application.student_name,
        "student_name_bn": application.student_name_bn,
        "guardian_name": application.guardian_name,
        "applying_class": application.applying_class,
        "mobile": application.mobile,
        "email": application.email,
        "status": application.status,
        "status_label": application.get_status_display(),
        "rejection_reason": application.rejection_reason,
        "created_at": application.created_at,
        "receipt_pdf_url": receipt_url,
        "receipt_view_url": receipt_view_url,
        "receipt_email_sent": application.receipt_email_sent,
        "transaction": transaction,
    }
