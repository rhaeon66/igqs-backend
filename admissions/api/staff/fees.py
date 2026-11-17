from django.utils.text import slugify
from rest_framework import serializers, viewsets

from admissions.models import AdmissionFee, PaymentDetail, PaymentMethod
from admissions.permissions import StaffAuthMixin


class StaffAdmissionFeeSerializer(serializers.ModelSerializer):
    grade_name = serializers.SerializerMethodField()

    class Meta:
        model = AdmissionFee
        fields = [
            "id",
            "grade",
            "grade_name",
            "amount",
            "currency",
            "label_en",
            "label_bn",
            "is_active",
        ]

    def get_grade_name(self, obj):
        return obj.grade.name_en if obj.grade else ""


class StaffPaymentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentDetail
        fields = ["id", "label_en", "label_bn", "value_en", "value_bn", "order"]
        extra_kwargs = {
            "id": {"read_only": True},
            "label_en": {"required": False, "allow_blank": True},
            "label_bn": {"required": False, "allow_blank": True},
            "value_en": {"required": False, "allow_blank": True},
            "value_bn": {"required": False, "allow_blank": True},
            "order": {"required": False},
        }


class StaffPaymentMethodSerializer(serializers.ModelSerializer):
    details = StaffPaymentDetailSerializer(many=True, required=False)

    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "code",
            "name_en",
            "name_bn",
            "is_active",
            "order",
            "details",
        ]
        extra_kwargs = {"code": {"required": False, "allow_blank": True}}

    def _code_for(self, name):
        base = (slugify(name)[:20] or "method")
        code = base
        number = 2
        while PaymentMethod.objects.filter(code=code).exists():
            suffix = f"-{number}"
            code = f"{base[: 20 - len(suffix)]}{suffix}"
            number += 1
        return code

    def _save_details(self, method, details):
        method.details.all().delete()
        PaymentDetail.objects.bulk_create(
            [
                PaymentDetail(
                    method=method,
                    label_en=(row.get("label_en") or "").strip(),
                    label_bn=(row.get("label_bn") or "").strip(),
                    value_en=(row.get("value_en") or "").strip(),
                    value_bn=(row.get("value_bn") or "").strip(),
                    order=index,
                )
                for index, row in enumerate(details)
                if any(
                    (row.get(key) or "").strip()
                    for key in ("label_en", "label_bn", "value_en", "value_bn")
                )
            ]
        )

    def create(self, validated_data):
        details = validated_data.pop("details", [])
        if not validated_data.get("code"):
            validated_data["code"] = self._code_for(validated_data.get("name_en") or "method")
        method = PaymentMethod.objects.create(**validated_data)
        self._save_details(method, details)
        return method

    def update(self, instance, validated_data):
        details = validated_data.pop("details", None)
        method = super().update(instance, validated_data)
        if details is not None:
            self._save_details(method, details)
        return method


class AdmissionFeeViewSet(StaffAuthMixin, viewsets.ModelViewSet):
    # The default (no-grade) admission fee only. Per-class fees are now set
    # from the class's own editor (CurriculumGradeViewSet / fee_amount), the
    # single place that keeps exactly one active fee per grade — this view
    # staying open to any grade would let staff create a second, divergent
    # fee for the same class through this raw CRUD screen.
    queryset = AdmissionFee.objects.filter(grade__isnull=True)
    serializer_class = StaffAdmissionFeeSerializer

    def perform_create(self, serializer):
        serializer.save(grade=None)

    def perform_update(self, serializer):
        serializer.save(grade=None)


class PaymentMethodViewSet(StaffAuthMixin, viewsets.ModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = StaffPaymentMethodSerializer
