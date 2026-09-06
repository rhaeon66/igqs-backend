from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import AdmissionApplication, AdmissionFee, Gender, PaymentMethod, PaymentMethodCode


def lang_of(request) -> str:
    if request and request.query_params.get("lang") == "bn":
        return "bn"
    return "en"


class AdmissionFeeSerializer(serializers.ModelSerializer):
    grade_slug = serializers.SerializerMethodField()
    grade_name = serializers.SerializerMethodField()
    label = serializers.SerializerMethodField()
    display = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionFee
        fields = [
            "grade_slug",
            "grade_name",
            "amount",
            "currency",
            "label",
            "display",
        ]

    def get_grade_slug(self, obj):
        return obj.grade.slug if obj.grade else None

    def get_grade_name(self, obj):
        lang = lang_of(self.context.get("request"))
        if not obj.grade:
            return None
        return obj.grade.localized("name", lang)

    def get_label(self, obj):
        lang = lang_of(self.context.get("request"))
        return obj.label_bn if lang == "bn" and obj.label_bn else obj.label_en

    def get_display(self, obj):
        return obj.display_amount()


class PaymentMethodSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    payment_type = serializers.SerializerMethodField()
    instructions = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = [
            "code",
            "name",
            "account_number",
            "account_name",
            "bank_name",
            "payment_type",
            "instructions",
        ]

    def get_name(self, obj):
        return obj.localized("name", lang_of(self.context.get("request")))

    def get_payment_type(self, obj):
        return obj.localized("payment_type", lang_of(self.context.get("request")))

    def get_instructions(self, obj):
        return obj.localized("instructions", lang_of(self.context.get("request")))


class AdmissionApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionApplication
        fields = [
            "application_id",
            "student_name",
            "student_name_bn",
            "date_of_birth",
            "gender",
            "birth_certificate",
            "previous_class",
            "applying_class",
            "student_photo",
            "student_address",
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
            "payment_method",
            "transaction_id",
            "payment_amount",
            "payment_date",
            "payer_mobile",
            "payment_screenshot",
            "status",
            "created_at",
            "receipt_id",
        ]
        read_only_fields = ["application_id", "receipt_id", "status", "created_at"]

    def validate_gender(self, value):
        if value not in Gender.values:
            raise serializers.ValidationError("Invalid gender.")
        return value

    def validate_payment_method(self, value):
        if value not in PaymentMethodCode.values:
            raise serializers.ValidationError("Invalid payment method.")
        if not PaymentMethod.objects.filter(code=value, is_active=True).exists():
            raise serializers.ValidationError("This payment method is not available.")
        return value

    def validate_transaction_id(self, value):
        trx = (value or "").strip()
        if len(trx) < 4:
            raise serializers.ValidationError("Enter a valid transaction ID.")
        qs = AdmissionApplication.objects.filter(transaction_id__iexact=trx)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This transaction ID is already linked to an application.")
        return trx

    def validate_payment_amount(self, value):
        try:
            amount = Decimal(value)
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError("Enter a valid payment amount.")
        if amount <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return amount

    def validate_payer_mobile(self, value):
        mobile = (value or "").strip()
        if len(mobile) < 8:
            raise serializers.ValidationError("Enter the payer's mobile number.")
        return mobile

    def validate_payment_date(self, value):
        if not value:
            raise serializers.ValidationError("Enter the payment date.")
        return value
