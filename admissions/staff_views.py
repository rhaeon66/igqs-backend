import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import StringIO

from django.contrib.auth import authenticate
from django.db.models import Case, Count, IntegerField, Max, Q, Sum, When
from django.utils.text import slugify
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import LocalStaffAuthentication
from content.models import CurriculumGrade

from .eligibility import admission_grades
from .models import AdmissionApplication, AdmissionFee, ApplicationStatus
from .permissions import IsStaffUser
from .receipts import issue_receipt, refresh_application_after_review
from .views import application_payload, receipt_pdf_response


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


class StaffAuthMixin:
    authentication_classes = [LocalStaffAuthentication]
    permission_classes = [IsStaffUser]


class StaffLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = request.data.get("password") or ""
        user = authenticate(request, username=username, password=password)
        if not user or not user.is_staff or not user.is_active:
            return Response(
                {"detail": "Invalid staff credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {
                "token": token.key,
                "username": user.get_username(),
                "name": user.get_full_name() or user.get_username(),
            }
        )


class StaffLogoutView(StaffAuthMixin, APIView):
    def post(self, request):
        Token.objects.filter(user=request.user).delete()
        return Response({"ok": True})


class StaffMeView(StaffAuthMixin, APIView):
    def get(self, request):
        user = request.user
        return Response(
            {
                "username": user.get_username(),
                "name": user.get_full_name() or user.get_username(),
            }
        )


class StaffAdmissionStatsView(StaffAuthMixin, APIView):
    def get(self, request):
        qs = AdmissionApplication.objects.all()
        today = timezone.localdate()
        by_status = {row["status"]: row["total"] for row in qs.values("status").annotate(total=Count("id"))}
        by_class = [
            {"applying_class": row["applying_class"], "total": row["total"]}
            for row in qs.values("applying_class").annotate(total=Count("id")).order_by("applying_class")
        ]
        approved = qs.filter(status=ApplicationStatus.APPROVED)
        pending = qs.filter(status=ApplicationStatus.PENDING)
        collected = approved.aggregate(total=Sum("payment_amount"))["total"] or 0
        pending_fees = pending.aggregate(total=Sum("payment_amount"))["total"] or 0
        submitted_fees = qs.aggregate(total=Sum("payment_amount"))["total"] or 0
        return Response(
            {
                "total": qs.count(),
                "pending": by_status.get(ApplicationStatus.PENDING, 0),
                "approved": by_status.get(ApplicationStatus.APPROVED, 0),
                "rejected": by_status.get(ApplicationStatus.REJECTED, 0),
                "today": qs.filter(created_at__date=today).count(),
                "by_class": by_class,
                "fee_collected": str(collected),
                "fee_pending": str(pending_fees),
                "fee_submitted": str(submitted_fees),
                "currency": "BDT",
            }
        )


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


class StaffApplicationListView(StaffAuthMixin, APIView):
    def get(self, request):
        qs = filtered_queryset(request)
        count = qs.count()
        page, page_size = parse_page_params(request)
        start = (page - 1) * page_size
        return Response(
            {
                "count": count,
                "page": page,
                "page_size": page_size,
                "results": [
                    staff_list_item(item, request) for item in qs[start : start + page_size]
                ],
                "classes": list(
                    AdmissionApplication.objects.order_by("applying_class")
                    .values_list("applying_class", flat=True)
                    .distinct()
                ),
            }
        )


class StaffApplicationDetailView(StaffAuthMixin, APIView):
    def get(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        issue_receipt(application, send_email=False)
        application.refresh_from_db()
        return Response(staff_detail_payload(application, request))


class StaffApplicationStatusView(StaffAuthMixin, APIView):
    def post(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        next_status = (request.data.get("status") or "").strip()
        reason = (request.data.get("rejection_reason") or "").strip()
        if next_status not in ApplicationStatus.values:
            return Response(
                {"detail": "Invalid application status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if next_status == ApplicationStatus.REJECTED and not reason:
            return Response(
                {"detail": "A rejection reason is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        application.status = next_status
        application.rejection_reason = reason if next_status == ApplicationStatus.REJECTED else ""
        application.reviewed_at = timezone.now()
        application.reviewed_by = request.user
        application.save(
            update_fields=["status", "rejection_reason", "reviewed_at", "reviewed_by"]
        )
        refresh_application_after_review(application)
        application.refresh_from_db()
        return Response(staff_detail_payload(application, request))


_CSV_FORMULA_PREFIXES = ("=", "+", "-", "@")


def _csv_safe(value):
    text = "" if value is None else str(value)
    if text and text[0] in _CSV_FORMULA_PREFIXES:
        # Neutralize CSV/formula injection: Excel/LibreOffice would otherwise
        # evaluate a cell like "=cmd|'/c calc'!A1" when staff open the export.
        return f"'{text}"
    return text


class StaffApplicationExportView(StaffAuthMixin, APIView):
    def get(self, request, application_id=None):
        if application_id:
            qs = AdmissionApplication.objects.filter(application_id=application_id)
            if not qs.exists():
                return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
            filename = f"{application_id}.csv"
        else:
            qs = filtered_queryset(request)
            filename = "igqs-applications.csv"

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "Application ID",
                "Receipt ID",
                "Status",
                "Student name",
                "Student name (Bengali)",
                "Guardian name",
                "Applying class",
                "Mobile",
                "Email",
                "Payment method",
                "Transaction ID",
                "Payment amount",
                "Payment date",
                "Submitted",
                "Rejection reason",
            ]
        )
        for application in qs:
            writer.writerow(
                [
                    _csv_safe(value)
                    for value in (
                        application.application_id,
                        application.receipt_id,
                        application.get_status_display(),
                        application.student_name,
                        application.student_name_bn,
                        application.guardian_name,
                        application.applying_class,
                        application.mobile,
                        application.email,
                        application.payment_method_label(),
                        application.transaction_id,
                        application.payment_amount,
                        application.payment_date,
                        timezone.localtime(application.created_at).strftime("%Y-%m-%d %H:%M"),
                        application.rejection_reason,
                    )
                ]
            )
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


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


def _parse_fee_amount(raw):
    if raw is None or str(raw).strip() == "":
        return None
    try:
        amount = Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise ValueError from exc
    if amount < 0 or amount > Decimal("99999999.99"):
        raise ValueError
    return amount.quantize(Decimal("0.01"))


def _set_class_fee(grade, amount):
    existing = AdmissionFee.objects.filter(grade=grade).order_by("-is_active", "id")
    if amount is None:
        existing.filter(is_active=True).update(is_active=False)
        return
    fee = existing.first()
    if fee is None:
        fee = AdmissionFee.objects.create(
            grade=grade,
            amount=amount,
            currency="BDT",
            is_active=True,
        )
    else:
        fee.amount = amount
        fee.is_active = True
        fee.save(update_fields=["amount", "is_active"])
    existing.exclude(pk=fee.pk).filter(is_active=True).update(is_active=False)


class StaffClassFeeView(StaffAuthMixin, APIView):
    def get(self, request):
        return Response({"fees": _class_fee_rows()})

    def put(self, request):
        rows = request.data.get("fees")
        if not isinstance(rows, list):
            return Response(
                {"detail": "Send a fee for each class."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        grades = {grade.id: grade for grade in admission_grades()}
        updates = []
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                return Response(
                    {"detail": "Each fee needs a class and an amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            grade_id = row.get("grade_id")
            if grade_id in ("", None):
                key = None
                grade = None
            else:
                try:
                    grade_id = int(grade_id)
                except (TypeError, ValueError):
                    return Response(
                        {"detail": "Unknown class."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                grade = grades.get(grade_id)
                if grade is None:
                    return Response(
                        {"detail": "Unknown class."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                key = grade_id
            if key in seen:
                continue
            seen.add(key)
            try:
                amount = _parse_fee_amount(row.get("amount"))
            except ValueError:
                return Response(
                    {"detail": "Enter a valid fee amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updates.append((grade, amount))

        for grade, amount in updates:
            _set_class_fee(grade, amount)
        return Response({"fees": _class_fee_rows()})

    def post(self, request):
        name_en = (request.data.get("name_en") or "").strip()
        name_bn = (request.data.get("name_bn") or "").strip()
        if not name_en or not name_bn:
            return Response(
                {"detail": "Enter the class name in English and Bengali."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount = _parse_fee_amount(request.data.get("amount"))
        except ValueError:
            return Response(
                {"detail": "Enter a valid fee amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if amount is None:
            return Response(
                {"detail": "Enter a fee amount."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        order = (CurriculumGrade.objects.aggregate(max_order=Max("order"))["max_order"] or 0) + 1
        grade = CurriculumGrade.objects.create(
            slug=_unique_grade_slug(name_en),
            name_en=name_en,
            name_bn=name_bn,
            description_en=name_en,
            description_bn=name_bn,
            order=order,
            open_for_admission=True,
            listed_on_curriculum=False,
        )
        _set_class_fee(grade, amount)
        return Response({"fees": _class_fee_rows()}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        raw_id = request.query_params.get("grade_id") or request.data.get("grade_id")
        try:
            grade_id = int(raw_id)
        except (TypeError, ValueError):
            return Response(
                {"detail": "Choose a class to remove."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        grade = CurriculumGrade.objects.filter(pk=grade_id, open_for_admission=True).first()
        if grade is None:
            return Response(
                {"detail": "Class not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        _set_class_fee(grade, None)
        if grade.listed_on_curriculum:
            grade.open_for_admission = False
            grade.save(update_fields=["open_for_admission"])
        else:
            grade.delete()
        return Response({"fees": _class_fee_rows()})


class StaffReceiptDownloadView(StaffAuthMixin, APIView):
    def get(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        return receipt_pdf_response(application, request)
