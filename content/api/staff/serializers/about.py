from rest_framework import serializers

from content.api.staff.serializers.mixins import ClearUploadedImagesMixin
from content.models import AboutPage, Facility, Leader


class StaffAboutPageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AboutPage
        fields = [
            "id",
            "introduction_en",
            "introduction_bn",
            "vision_en",
            "vision_bn",
            "mission_en",
            "mission_bn",
            "history_en",
            "history_bn",
            "quranic_approach_en",
            "quranic_approach_bn",
            "principal_message_en",
            "principal_message_bn",
        ]


class StaffLeaderSerializer(ClearUploadedImagesMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("photo",)
    clear_photo = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = Leader
        fields = [
            "id",
            "name_en",
            "name_bn",
            "role_en",
            "role_bn",
            "bio_en",
            "bio_bn",
            "photo",
            "clear_photo",
            "photo_url",
            "order",
        ]


class StaffFacilitySerializer(ClearUploadedImagesMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("image",)
    clear_image = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = Facility
        fields = [
            "id",
            "title_en",
            "title_bn",
            "description_en",
            "description_bn",
            "image",
            "clear_image",
            "image_url",
            "order",
        ]
