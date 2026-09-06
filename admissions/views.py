from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from content.models import CurriculumGrade

from .models import AdmissionApplication, AdmissionFee, PaymentMethod
from .receipts import issue_receipt
from .serializers import (
    AdmissionApplicationSerializer,
    AdmissionFeeSerializer,
    PaymentMethodSerializer,
)


def normalize_receipt_id(value: str) -> str:
    return (value or "").strip().upper().replace(" ", "")


def find_application_by_receipt(receipt_id: str):
    rid = normalize_receipt_id(receipt_id)
    if not rid:
        return None
    return AdmissionApplication.objects.filter(receipt_id__iexact=rid).first()


def find_application_by_query(value: str):
    query = normalize_receipt_id(value)
    if not query:
        return None
    application = AdmissionApplication.objects.filter(application_id__iexact=query).first()
    return application or find_application_by_receipt(query)


def receipt_pdf_response(application, request):
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
    if request and application.receipt_id:
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


class ApplyingClassListView(APIView):
    def get(self, request):
        lang = "bn" if request.query_params.get("lang") == "bn" else "en"
        grades = CurriculumGrade.objects.all()
        return Response(
            [{"slug": g.slug, "name": g.localized("name", lang)} for g in grades]
        )


class AdmissionInfoView(APIView):
    def get(self, request):
        ctx = {"request": request}
        fees = AdmissionFee.objects.filter(is_active=True).select_related("grade")
        default_fee = fees.filter(grade__isnull=True).first()
        return Response(
            {
                "default_fee": AdmissionFeeSerializer(default_fee, context=ctx).data
                if default_fee
                else None,
                "fees": AdmissionFeeSerializer(fees, many=True, context=ctx).data,
                "methods": PaymentMethodSerializer(
                    PaymentMethod.objects.filter(is_active=True),
                    many=True,
                    context=ctx,
                ).data,
            }
        )


class AdmissionApplicationCreateView(generics.CreateAPIView):
    serializer_class = AdmissionApplicationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        application = serializer.save()
        issue_receipt(application, send_email=True)
        application.refresh_from_db()
        return Response(
            application_payload(application, request),
            status=status.HTTP_201_CREATED,
        )


class AdmissionApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = AdmissionApplicationSerializer
    queryset = AdmissionApplication.objects.all()
    lookup_field = "application_id"

    def retrieve(self, request, *args, **kwargs):
        application = self.get_object()
        issue_receipt(application, send_email=False)
        application.refresh_from_db()
        return Response(application_payload(application, request))


class AdmissionReceiptDownloadView(APIView):
    def get(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        return receipt_pdf_response(application, request)


class AdmissionLookupView(APIView):
    def get(self, request):
        application = find_application_by_query(request.query_params.get("q") or "")
        if not application:
            return Response(
                {"detail": "No application was found for that ID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        issue_receipt(application, send_email=False)
        application.refresh_from_db()
        return Response(application_payload(application, request))


class AdmissionReceiptLookupView(APIView):
    def get(self, request, receipt_id):
        application = find_application_by_receipt(receipt_id)
        if not application:
            return Response(
                {"detail": "No receipt was found for that Receipt ID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        issue_receipt(application, send_email=False)
        application.refresh_from_db()
        return Response(application_payload(application, request))


class AdmissionReceiptPdfByIdView(APIView):
    def get(self, request, receipt_id):
        application = find_application_by_receipt(receipt_id)
        if not application:
            return Response(
                {"detail": "No receipt was found for that Receipt ID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return receipt_pdf_response(application, request)
