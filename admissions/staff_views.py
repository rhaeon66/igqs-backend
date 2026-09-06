import csv
from io import StringIO

from django.contrib.auth import authenticate
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdmissionApplication, ApplicationStatus
from .permissions import IsStaffUser
from .receipts import issue_receipt, refresh_application_after_review
from .views import application_payload, receipt_pdf_response


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
        "payment_method_label": application.get_payment_method_display(),
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
        "payment_method_label": application.get_payment_method_display(),
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
    return qs.order_by(sort)


class StaffAuthMixin:
    authentication_classes = [TokenAuthentication]
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


class StaffApplicationListView(StaffAuthMixin, APIView):
    def get(self, request):
        qs = filtered_queryset(request)
        return Response(
            {
                "count": qs.count(),
                "results": [staff_list_item(item, request) for item in qs],
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
                    application.application_id,
                    application.receipt_id,
                    application.get_status_display(),
                    application.student_name,
                    application.student_name_bn,
                    application.guardian_name,
                    application.applying_class,
                    application.mobile,
                    application.email,
                    application.get_payment_method_display(),
                    application.transaction_id,
                    application.payment_amount,
                    application.payment_date,
                    timezone.localtime(application.created_at).strftime("%Y-%m-%d %H:%M"),
                    application.rejection_reason,
                ]
            )
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class StaffReceiptDownloadView(StaffAuthMixin, APIView):
    def get(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        return receipt_pdf_response(application, request)
