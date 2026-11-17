from rest_framework import serializers

from admissions.eligibility import parse_fee_amount, set_class_fee
from content.api.public.serializers import abs_url
from content.api.staff.serializers.mixins import (
    ClearUploadedImagesMixin,
    SlugFromTitleMixin,
    unique_slug,
    wants_new_slug,
)
from content.models import CurriculumDocument, CurriculumGrade, Subject


class StaffSubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = [
            "id",
            "grade",
            "name_en",
            "name_bn",
            "category",
            "description_en",
            "description_bn",
            "order",
        ]


class StaffCurriculumDocumentSerializer(
    ClearUploadedImagesMixin, serializers.ModelSerializer
):
    # The model has always had a `file` upload alongside `file_url`, but only
    # the URL was exposed, so a syllabus PDF had to be hosted elsewhere first.
    uploaded_image_fields = ("file",)
    clear_file = serializers.BooleanField(required=False, write_only=True)
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumDocument
        fields = [
            "id",
            "grade",
            "title_en",
            "title_bn",
            "file",
            "clear_file",
            "file_url",
            "download_url",
            "order",
        ]

    def get_download_url(self, obj):
        return abs_url(self.context.get("request"), obj.download_url)


class StaffCurriculumGradeSerializer(SlugFromTitleMixin, serializers.ModelSerializer):
    subjects = StaffSubjectSerializer(many=True, read_only=True)
    documents = StaffCurriculumDocumentSerializer(many=True, read_only=True)
    # Admission fee lives on a separate AdmissionFee row (one per grade), not
    # a column on CurriculumGrade — exposed here (backed by the model's
    # fee_amount property for reads) so staff manage a class's curriculum
    # content and its admission fee in one place instead of two.
    fee_amount = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = CurriculumGrade
        fields = [
            "id",
            "slug",
            "name_en",
            "name_bn",
            "description_en",
            "description_bn",
            "order",
            "open_for_admission",
            "listed_on_curriculum",
            "fee_amount",
            "subjects",
            "documents",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        if wants_new_slug(self, attrs):
            name = attrs.get("name_en") or getattr(self.instance, "name_en", "")
            attrs["slug"] = unique_slug(CurriculumGrade, name, self.instance)
        return attrs

    def validate_fee_amount(self, value):
        try:
            return parse_fee_amount(value)
        except ValueError:
            raise serializers.ValidationError("Enter a valid fee amount.")

    def create(self, validated_data):
        fee_amount = validated_data.pop("fee_amount", None)
        grade = super().create(validated_data)
        set_class_fee(grade, fee_amount)
        return grade

    def update(self, instance, validated_data):
        fee_amount = validated_data.pop("fee_amount", serializers.empty)
        grade = super().update(instance, validated_data)
        if fee_amount is not serializers.empty:
            set_class_fee(grade, fee_amount)
        return grade
