from django.contrib import admin

from .models import AdmissionApplication, AdmissionFee, GuardianSession, PaymentMethod, PhoneOtp


@admin.register(PhoneOtp)
class PhoneOtpAdmin(admin.ModelAdmin):
    list_display = ("phone", "expires_at", "attempts", "consumed_at", "created_at")
    search_fields = ("phone",)
    readonly_fields = ("code_hash", "created_at")


@admin.register(GuardianSession)
class GuardianSessionAdmin(admin.ModelAdmin):
    list_display = ("phone", "expires_at", "created_at")
    search_fields = ("phone",)
    readonly_fields = ("token_hash", "created_at")


@admin.register(AdmissionFee)
class AdmissionFeeAdmin(admin.ModelAdmin):
    list_display = ("grade", "amount", "currency", "is_active")


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name_en", "code", "account_number", "payment_type_en", "is_active", "order")


@admin.register(AdmissionApplication)
class AdmissionApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "application_id",
        "receipt_id",
        "student_name",
        "applying_class",
        "payment_method",
        "transaction_id",
        "payment_amount",
        "status",
        "receipt_email_sent",
        "reviewed_at",
        "created_at",
    )
    list_filter = ("status", "applying_class", "gender", "payment_method")
    search_fields = (
        "application_id",
        "receipt_id",
        "student_name",
        "student_name_bn",
        "guardian_name",
        "mobile",
        "email",
        "transaction_id",
        "payer_mobile",
    )
    readonly_fields = (
        "application_id",
        "receipt_id",
        "receipt_pdf",
        "receipt_email_sent",
        "reviewed_at",
        "reviewed_by",
        "created_at",
    )
    fieldsets = (
        (
            "Application",
            {
                "fields": (
                    "application_id",
                    "receipt_id",
                    "status",
                    "created_at",
                    "receipt_pdf",
                    "receipt_email_sent",
                    "rejection_reason",
                    "reviewed_at",
                    "reviewed_by",
                )
            },
        ),
        (
            "Student information",
            {
                "fields": (
                    "student_name",
                    "student_name_bn",
                    "date_of_birth",
                    "gender",
                    "previous_class",
                    "applying_class",
                    "student_address",
                    "student_photo",
                    "birth_certificate",
                )
            },
        ),
        (
            "Guardian information",
            {
                "fields": (
                    "father_name",
                    "mother_name",
                    "guardian_name",
                    "father_occupation",
                    "mother_occupation",
                    "mobile",
                    "email",
                    "guardian_address",
                    "emergency_contact",
                    "previous_academic_info",
                    "special_requirements",
                )
            },
        ),
        (
            "Transaction information",
            {
                "fields": (
                    "payment_method",
                    "transaction_id",
                    "payment_amount",
                    "payment_date",
                    "payer_mobile",
                    "payment_screenshot",
                )
            },
        ),
    )
