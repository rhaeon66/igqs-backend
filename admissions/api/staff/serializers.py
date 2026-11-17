from rest_framework import serializers

from admissions.models import AdmissionApplication, PaymentMethod
from admissions.phone import PhoneError, normalize_bd_phone


class StaffReceiptSerializer(serializers.ModelSerializer):
    """Fields staff may correct on an admission receipt.

    Deliberately narrower than the applicant form: IDs, status and uploaded
    files are not editable here, and the amount is not forced to match the
    class fee (staff may record a discount or a corrected payment).
    """

    class Meta:
        model = AdmissionApplication
        fields = [
            "student_name",
            "student_name_bn",
            "guardian_name",
            "applying_class",
            "mobile",
            "email",
            "payment_method",
            "transaction_id",
            "payment_amount",
            "payment_date",
            "payer_mobile",
        ]
        extra_kwargs = {"payment_date": {"required": False}}

    def _required_text(self, value, message):
        text = (value or "").strip()
        if not text:
            raise serializers.ValidationError(message)
        return text

    def validate_student_name(self, value):
        return self._required_text(value, "Enter the student's name.")

    def validate_student_name_bn(self, value):
        return self._required_text(value, "Enter the student's name in Bangla.")

    def validate_guardian_name(self, value):
        return self._required_text(value, "Enter the guardian's name.")

    def validate_applying_class(self, value):
        return self._required_text(value, "Enter the class.")

    def validate_mobile(self, value):
        try:
            return normalize_bd_phone(value)
        except PhoneError as exc:
            raise serializers.ValidationError(exc.message)

    def validate_payer_mobile(self, value):
        mobile = (value or "").strip()
        if len(mobile) < 8:
            raise serializers.ValidationError("Enter the payer's mobile number.")
        return mobile

    def validate_payment_method(self, value):
        # Inactive methods stay valid so an old receipt can keep its method.
        if not PaymentMethod.objects.filter(code=value).exists():
            raise serializers.ValidationError("Unknown payment method.")
        return value

    def validate_transaction_id(self, value):
        trx = (value or "").strip()
        if len(trx) < 4:
            raise serializers.ValidationError("Enter a valid transaction ID.")
        qs = AdmissionApplication.objects.filter(transaction_id__iexact=trx)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("This transaction ID is already linked to another application.")
        return trx

    def validate_payment_amount(self, value):
        if value is None or value <= 0:
            raise serializers.ValidationError("Payment amount must be greater than zero.")
        return value
