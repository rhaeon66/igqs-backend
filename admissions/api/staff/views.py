import csv
from io import StringIO

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.models import Count, Max, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from admissions.api.payloads import receipt_pdf_response
from admissions.api.staff.queries import (
    _class_fee_rows,
    _csv_safe,
    _unique_grade_slug,
    filtered_queryset,
    parse_page_params,
    staff_detail_payload,
    staff_list_item,
)
from admissions.api.staff.serializers import StaffReceiptSerializer
from admissions.eligibility import admission_grades, parse_fee_amount, set_class_fee
from admissions.models import AdmissionApplication, ApplicationStatus
from admissions.permissions import StaffAuthMixin
from admissions.receipts import generate_receipt_pdf, issue_receipt, refresh_application_after_review
from content.models import CurriculumGrade


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
                "Student name (Bangla)",
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
                amount = parse_fee_amount(row.get("amount"))
            except ValueError:
                return Response(
                    {"detail": "Enter a valid fee amount."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            updates.append((grade, amount))

        for grade, amount in updates:
            set_class_fee(grade, amount)
        return Response({"fees": _class_fee_rows()})

    def post(self, request):
        name_en = (request.data.get("name_en") or "").strip()
        name_bn = (request.data.get("name_bn") or "").strip()
        if not name_en or not name_bn:
            return Response(
                {"detail": "Enter the class name in English and Bangla."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            amount = parse_fee_amount(request.data.get("amount"))
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
        set_class_fee(grade, amount)
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
        set_class_fee(grade, None)
        if grade.listed_on_curriculum:
            grade.open_for_admission = False
            grade.save(update_fields=["open_for_admission"])
        else:
            grade.delete()
        return Response({"fees": _class_fee_rows()})


class StaffReceiptView(StaffAuthMixin, APIView):
    """GET serves the receipt PDF (``?inline=1`` to view in the browser);
    PATCH corrects the details printed on it and rebuilds the PDF."""

    def get(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        return receipt_pdf_response(application, request)

    def patch(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        serializer = StaffReceiptSerializer(application, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                serializer.save()
        except IntegrityError:
            return Response(
                {"transaction_id": ["This transaction ID is already linked to another application."]},
                status=status.HTTP_409_CONFLICT,
            )
        # The stored PDF is a snapshot; rebuild it so downloads, the public
        # receipt page and future emails all show the corrected details.
        generate_receipt_pdf(application, force=True)
        application.refresh_from_db()
        return Response(staff_detail_payload(application, request))
