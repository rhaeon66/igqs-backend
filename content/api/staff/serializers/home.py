from rest_framework import serializers

from content.api.public.serializers import abs_url
from content.api.staff.serializers.mixins import ClearUploadedImagesMixin, SanitizeHtmlMixin
from content.models import (
    HeroSlide,
    HomeContent,
    HomeSection,
    HomeStat,
    SiteSettings,
    Testimonial,
    WhyChooseItem,
)


class StaffSiteSettingsSerializer(ClearUploadedImagesMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("logo",)
    logo_src = serializers.SerializerMethodField()
    clear_logo = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = SiteSettings
        fields = [
            "id",
            "school_name_en",
            "school_name_bn",
            "tagline_en",
            "tagline_bn",
            "logo",
            "clear_logo",
            "logo_url",
            "logo_src",
            "address_en",
            "address_bn",
            "phone_primary",
            "phone_secondary",
            "email",
            "map_embed_url",
            "office_hours_en",
            "office_hours_bn",
            "facebook_url",
            "youtube_url",
            "instagram_url",
            "whatsapp_url",
            "admission_open",
            "admission_announcement_en",
            "admission_announcement_bn",
        ]

    def get_logo_src(self, obj):
        return abs_url(self.context.get("request"), obj.logo_src)


class StaffHomeContentSerializer(SanitizeHtmlMixin, ClearUploadedImagesMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("hero_image", "principal_photo", "chairman_photo")
    html_fields = (
        "welcome_en",
        "welcome_bn",
        "about_preview_en",
        "about_preview_bn",
        "principal_message_en",
        "principal_message_bn",
        "chairman_message_en",
        "chairman_message_bn",
        "goals_en",
        "goals_bn",
        "beacon_en",
        "beacon_bn",
        "dreams_en",
        "dreams_bn",
        "child_gain_en",
        "child_gain_bn",
        "holistic_en",
        "holistic_bn",
        "admission_procedures_en",
        "admission_procedures_bn",
        "tuition_en",
        "tuition_bn",
        "uniform_en",
        "uniform_bn",
    )
    clear_hero_image = serializers.BooleanField(required=False, write_only=True)
    clear_principal_photo = serializers.BooleanField(required=False, write_only=True)
    clear_chairman_photo = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = HomeContent
        fields = [
            "id",
            "hero_title_en",
            "hero_title_bn",
            "hero_subtitle_en",
            "hero_subtitle_bn",
            "hero_image",
            "clear_hero_image",
            "hero_image_url",
            "welcome_en",
            "welcome_bn",
            "about_preview_en",
            "about_preview_bn",
            "principal_name_en",
            "principal_name_bn",
            "principal_title_en",
            "principal_title_bn",
            "principal_message_en",
            "principal_message_bn",
            "principal_photo",
            "clear_principal_photo",
            "principal_photo_url",
            "chairman_name_en",
            "chairman_name_bn",
            "chairman_title_en",
            "chairman_title_bn",
            "chairman_message_en",
            "chairman_message_bn",
            "chairman_photo",
            "clear_chairman_photo",
            "chairman_photo_url",
            "goals_en",
            "goals_bn",
            "beacon_en",
            "beacon_bn",
            "dreams_en",
            "dreams_bn",
            "child_gain_en",
            "child_gain_bn",
            "holistic_en",
            "holistic_bn",
            "admission_procedures_en",
            "admission_procedures_bn",
            "tuition_en",
            "tuition_bn",
            "uniform_en",
            "uniform_bn",
        ]


class StaffHomeSectionSerializer(SanitizeHtmlMixin, serializers.ModelSerializer):
    html_fields = ("description_en", "description_bn")
    class Meta:
        model = HomeSection
        fields = [
            "id",
            "title_en",
            "title_bn",
            "description_en",
            "description_bn",
            "order",
        ]


class StaffHeroSlideSerializer(serializers.ModelSerializer):
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = HeroSlide
        fields = ["id", "image", "image_src", "order"]
        extra_kwargs = {"image": {"required": True}}

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image.url if obj.image else "")


class StaffHomeStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeStat
        fields = ["id", "value", "label_en", "label_bn", "icon", "order"]


class StaffWhyChooseSerializer(SanitizeHtmlMixin, ClearUploadedImagesMixin, serializers.ModelSerializer):
    html_fields = ("description_en", "description_bn")
    uploaded_image_fields = ("image",)
    clear_image = serializers.BooleanField(required=False, write_only=True)
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = WhyChooseItem
        fields = [
            "id",
            "title_en",
            "title_bn",
            "description_en",
            "description_bn",
            "icon",
            "image",
            "clear_image",
            "image_url",
            "image_src",
            "order",
        ]

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffTestimonialSerializer(SanitizeHtmlMixin, ClearUploadedImagesMixin, serializers.ModelSerializer):
    html_fields = ("quote_en", "quote_bn")
    uploaded_image_fields = ("image",)
    clear_image = serializers.BooleanField(required=False, write_only=True)
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = Testimonial
        fields = [
            "id",
            "name_en",
            "name_bn",
            "role",
            "quote_en",
            "quote_bn",
            "spoken_on",
            "rating",
            "facebook_url",
            "image",
            "clear_image",
            "image_url",
            "image_src",
            "order",
        ]

    def validate_rating(self, value):
        if value > 5:
            raise serializers.ValidationError("Use a rating from 0 to 5.")
        return value

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)
