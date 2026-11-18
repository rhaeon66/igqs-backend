from datetime import datetime

from django.db.models import Case, IntegerField, Q, When
from django.utils.text import slugify

from admissions.api.payloads import application_payload
from admissions.eligibility import admission_grades
from admissions.models import AdmissionApplication, AdmissionFee, ApplicationStatus
from content.models import CurriculumGrade


def parse_query_date(value):
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return None


def media_url(request, field):
    if not field:
        return ""
    url = field.url
    return request.build_absolute_uri(url) if request else url


def staff_list_item(application, request=None):
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
        "payment_method": application.payment_method,
        "payment_method_label": application.payment_method_label(),
        "transaction_id": application.transaction_id,
        "payment_amount": str(application.payment_amount),
        "created_at": application.created_at,
        "rejection_reason": application.rejection_reason,
    }


def staff_detail_payload(application, request):
    payload = application_payload(application, request)
    payload.update(staff_list_item(application, request))
    payload.update(
        {
            "date_of_birth": application.date_of_birth.isoformat(),
            "gender": application.gender,
            "gender_label": application.get_gender_display(),
            "previous_class": application.previous_class,
            "student_address": application.student_address,
            "student_photo": media_url(request, application.student_photo),
            "birth_certificate": media_url(request, application.birth_certificate),
            "guardian_nid": media_url(request, application.guardian_nid),
            "guardian_photo": media_url(request, application.guardian_photo),
            "academic_documents": media_url(request, application.academic_documents),
            "father_name": application.father_name,
            "mother_name": application.mother_name,
            "father_occupation": application.father_occupation,
            "mother_occupation": application.mother_occupation,
            "guardian_address": application.guardian_address,
            "emergency_contact": application.emergency_contact,
            "previous_academic_info": application.previous_academic_info,
            "special_requirements": application.special_requirements,
            "rejection_reason": application.rejection_reason,
            "reviewed_at": application.reviewed_at,
            "reviewed_by": application.reviewed_by.get_username()
            if application.reviewed_by
            else "",
        }
    )
    payload["transaction"] = {
        **payload.get("transaction", {}),
        "payment_method_label": application.payment_method_label(),
    }
    return payload


def filtered_queryset(request):
    qs = AdmissionApplication.objects.select_related("reviewed_by").all()
    query = (request.query_params.get("q") or "").strip()
    status_filter = (request.query_params.get("status") or "").strip()
    applying_class = (request.query_params.get("applying_class") or "").strip()
    if query:
        qs = qs.filter(
            Q(application_id__icontains=query)
            | Q(receipt_id__icontains=query)
            | Q(student_name__icontains=query)
            | Q(student_name_bn__icontains=query)
            | Q(guardian_name__icontains=query)
            | Q(mobile__icontains=query)
            | Q(email__icontains=query)
            | Q(transaction_id__icontains=query)
            | Q(payer_mobile__icontains=query)
        )
    if status_filter in ApplicationStatus.values:
        qs = qs.filter(status=status_filter)
    if applying_class:
        qs = qs.filter(applying_class=applying_class)

    date_from = parse_query_date(request.query_params.get("date_from"))
    date_to = parse_query_date(request.query_params.get("date_to"))
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)

    sort = request.query_params.get("sort") or "-created_at"
    allowed = {
        "created_at",
        "-created_at",
        "student_name",
        "-student_name",
        "applying_class",
        "-applying_class",
        "payment_amount",
        "-payment_amount",
        "status",
        "-status",
    }
    if sort not in allowed:
        sort = "-created_at"
    if sort in ("status", "-status"):
        ranked = qs.annotate(
            status_rank=Case(
                When(status=ApplicationStatus.PENDING, then=0),
                When(status=ApplicationStatus.APPROVED, then=1),
                When(status=ApplicationStatus.REJECTED, then=2),
                default=3,
                output_field=IntegerField(),
            )
        )
        direction = "status_rank" if sort == "status" else "-status_rank"
        return ranked.order_by(direction, "-created_at")
    return qs.order_by(sort, "-created_at")

def parse_page_params(request):
    try:
        page = int(request.query_params.get("page") or 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get("page_size") or 25)
    except (TypeError, ValueError):
        page_size = 25
    page = max(1, page)
    page_size = max(1, min(page_size, 100))
    return page, page_size

_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _csv_safe(value):
    text = "" if value is None else str(value)
    if text and text[0] in _CSV_FORMULA_PREFIXES:
        # Neutralize CSV/formula injection: Excel/LibreOffice would otherwise
        # evaluate a cell like "=cmd|'/c calc'!A1" when staff open the export.
        return f"'{text}"
    return text

def _amount_text(fee):
    if fee is None:
        return ""
    amount = fee.amount
    if amount == amount.to_integral():
        return str(int(amount))
    return format(amount, "f")


def _unique_grade_slug(name: str) -> str:
    base = (slugify(name)[:40] or "class")
    slug = base
    number = 2
    while CurriculumGrade.objects.filter(slug=slug).exists():
        suffix = f"-{number}"
        slug = f"{base[: 50 - len(suffix)]}{suffix}"
        number += 1
    return slug


def _class_fee_rows():
    grades = list(admission_grades())
    active = AdmissionFee.objects.filter(is_active=True).select_related("grade")
    by_grade = {}
    default_fee = None
    for fee in active:
        if fee.grade_id is None:
            default_fee = default_fee or fee
        else:
            by_grade.setdefault(fee.grade_id, fee)
    rows = [
        {
            "grade_id": None,
            "slug": "",
            "name_en": "",
            "name_bn": "",
            "amount": _amount_text(default_fee),
        }
    ]
    for grade in grades:
        fee = by_grade.get(grade.id)
        rows.append(
            {
                "grade_id": grade.id,
                "slug": grade.slug,
                "name_en": grade.name_en,
                "name_bn": grade.name_bn,
                "amount": _amount_text(fee),
            }
        )
    return rows
