from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from admissions.api.payloads import (
    application_payload,
    find_application_by_query,
    find_application_by_receipt,
    receipt_pdf_response,
)
from admissions.api.public.serializers import (
    AdmissionApplicationSerializer,
    AdmissionFeeSerializer,
    PaymentMethodSerializer,
)
from admissions.eligibility import admission_grades
from admissions.models import AdmissionApplication, AdmissionFee, PaymentMethod
from admissions.phone import (
    PhoneError,
    clear_lookup_failures,
    ensure_lookup_allowed,
    normalize_bd_phone,
    record_lookup_failure,
)
from admissions.receipts import issue_receipt, notify_staff_new_application


class ApplyingClassListView(APIView):
    def get(self, request):
        lang = "en" if request.query_params.get("lang") == "en" else "bn"
        return Response(
            [
                {"slug": grade.slug, "name": grade.localized("name", lang)}
                for grade in admission_grades()
            ]
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
                    PaymentMethod.objects.filter(is_active=True).prefetch_related("details"),
                    many=True,
                    context=ctx,
                ).data,
            }
        )


def phone_error_response(exc: PhoneError):
    return Response(
        {"detail": exc.message, "code": exc.code},
        status=exc.status,
    )


class AdmissionApplicationCreateView(generics.CreateAPIView):
    serializer_class = AdmissionApplicationSerializer

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        try:
            mobile = normalize_bd_phone(data.get("mobile") or "")
        except PhoneError as exc:
            return phone_error_response(exc)
        data["mobile"] = mobile
        data["payer_mobile"] = mobile
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                application = serializer.save()
        except IntegrityError:
            # Two submissions raced for the same application/receipt number,
            # or the transaction ID was claimed a moment ago. Ask the
            # applicant to resubmit rather than losing their payment proof
            # to an unhandled 500.
            return Response(
                {
                    "detail": (
                        "This application could not be saved because of a "
                        "conflict. Please submit the form again."
                    )
                },
                status=status.HTTP_409_CONFLICT,
            )
        issue_receipt(application, send_email=True)
        notify_staff_new_application(application)
        application.refresh_from_db()
        return Response(
            application_payload(application, request),
            status=status.HTTP_201_CREATED,
        )


class MyApplicationsView(APIView):
    """Guardian payment history, unlocked by mobile + student's date of birth.

    POST rather than GET so the date of birth never lands in URLs, server
    logs or browser history. A wrong DOB and an unknown number get the same
    404, so the endpoint does not reveal which numbers have applied.
    """

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admission_lookup"

    def post(self, request):
        raw_phone = str(request.data.get("phone") or "").strip()
        raw_dob = str(request.data.get("date_of_birth") or "").strip()
        if not raw_phone or not raw_dob:
            return Response(
                {"detail": "Enter the mobile number and the student's date of birth."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            phone = normalize_bd_phone(raw_phone)
        except PhoneError as exc:
            return phone_error_response(exc)
        try:
            date_of_birth = parse_date(raw_dob)
        except ValueError:
            date_of_birth = None
        if not date_of_birth:
            return Response(
                {"detail": "Enter a valid date of birth.", "code": "invalid_dob"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            ensure_lookup_allowed(phone)
        except PhoneError as exc:
            return phone_error_response(exc)

        applications = AdmissionApplication.objects.filter(
            mobile=phone, date_of_birth=date_of_birth
        )
        if not applications.exists():
            record_lookup_failure(phone)
            return Response(
                {
                    "detail": "No applications match that mobile number and date of birth.",
                    "code": "no_match",
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        clear_lookup_failures(phone)
        return Response(
            {
                "phone": phone,
                "count": applications.count(),
                "results": [application_payload(item, request) for item in applications],
            }
        )


class AdmissionApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = AdmissionApplicationSerializer
    queryset = AdmissionApplication.objects.all()
    lookup_field = "application_id"
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admission_lookup"

    def retrieve(self, request, *args, **kwargs):
        application = self.get_object()
        issue_receipt(application, send_email=False)
        application.refresh_from_db()
        return Response(application_payload(application, request))


class AdmissionReceiptDownloadView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admission_lookup"

    def get(self, request, application_id):
        application = get_object_or_404(
            AdmissionApplication, application_id=application_id
        )
        return receipt_pdf_response(application, request, public=True)


class AdmissionLookupView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admission_lookup"

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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admission_lookup"

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
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "admission_lookup"

    def get(self, request, receipt_id):
        application = find_application_by_receipt(receipt_id)
        if not application:
            return Response(
                {"detail": "No receipt was found for that Receipt ID."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return receipt_pdf_response(application, request, public=True)
