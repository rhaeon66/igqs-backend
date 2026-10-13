from django.utils.text import slugify
from rest_framework import serializers

from admissions.models import AdmissionFee, PaymentDetail, PaymentMethod

from .models import (
    AboutPage,
    CurriculumDocument,
    CurriculumGrade,
    Event,
    Facility,
    GalleryAlbum,
    GalleryImage,
    HomeContent,
    Leader,
    NewsPost,
    SiteSettings,
    Subject,
    WhyChooseItem,
)
from .serializers import abs_url


def unique_slug(model, value, instance=None):
    base = slugify(value) or "item"
    slug = base
    index = 2
    queryset = model.objects.all()
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)
    while queryset.filter(slug=slug).exists():
        slug = f"{base}-{index}"
        index += 1
    return slug


class SlugFromTitleMixin:
    def validate(self, attrs):
        attrs = super().validate(attrs)
        if not attrs.get("slug"):
            title = attrs.get("title_en") or getattr(self.instance, "title_en", "")
            attrs["slug"] = unique_slug(self.Meta.model, title, self.instance)
        return attrs


class ClearUploadedImagesMixin:
    uploaded_image_fields: tuple[str, ...] = ()

    def _clear_uploaded_images(self, instance, validated_data):
        for name in self.uploaded_image_fields:
            if not validated_data.pop(f"clear_{name}", False):
                continue
            current = getattr(instance, name)
            if current:
                current.delete(save=False)
            setattr(instance, name, None)

    def update(self, instance, validated_data):
        self._clear_uploaded_images(instance, validated_data)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        for name in self.uploaded_image_fields:
            validated_data.pop(f"clear_{name}", None)
        return super().create(validated_data)


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


class StaffHomeContentSerializer(ClearUploadedImagesMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("hero_image", "principal_photo")
    clear_hero_image = serializers.BooleanField(required=False, write_only=True)
    clear_principal_photo = serializers.BooleanField(required=False, write_only=True)

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
        ]


class StaffWhyChooseSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhyChooseItem
        fields = [
            "id",
            "title_en",
            "title_bn",
            "description_en",
            "description_bn",
            "icon",
            "order",
        ]


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


class StaffCurriculumDocumentSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumDocument
        fields = [
            "id",
            "grade",
            "title_en",
            "title_bn",
            "file_url",
            "download_url",
            "order",
        ]

    def get_download_url(self, obj):
        return abs_url(self.context.get("request"), obj.download_url)


class StaffCurriculumGradeSerializer(SlugFromTitleMixin, serializers.ModelSerializer):
    subjects = StaffSubjectSerializer(many=True, read_only=True)
    documents = StaffCurriculumDocumentSerializer(many=True, read_only=True)

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
            "subjects",
            "documents",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def validate(self, attrs):
        if not attrs.get("slug"):
            name = attrs.get("name_en") or getattr(self.instance, "name_en", "")
            attrs["slug"] = unique_slug(CurriculumGrade, name, self.instance)
        return attrs


class StaffEventSerializer(ClearUploadedImagesMixin, SlugFromTitleMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("image",)
    image_src = serializers.SerializerMethodField()
    clear_image = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = Event
        fields = [
            "id",
            "slug",
            "title_en",
            "title_bn",
            "start_at",
            "end_at",
            "location_en",
            "location_bn",
            "description_en",
            "description_bn",
            "image",
            "clear_image",
            "image_url",
            "image_src",
            "is_published",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffNewsSerializer(ClearUploadedImagesMixin, SlugFromTitleMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("featured_image",)
    image_src = serializers.SerializerMethodField()
    clear_featured_image = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = NewsPost
        fields = [
            "id",
            "slug",
            "title_en",
            "title_bn",
            "category",
            "description_en",
            "description_bn",
            "featured_image",
            "clear_featured_image",
            "featured_image_url",
            "image_src",
            "published_at",
            "is_published",
            "is_important",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffGalleryImageSerializer(ClearUploadedImagesMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("image",)
    image_src = serializers.SerializerMethodField()
    clear_image = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = GalleryImage
        fields = [
            "id",
            "album",
            "image",
            "clear_image",
            "image_url",
            "image_src",
            "caption_en",
            "caption_bn",
            "order",
        ]

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffGalleryAlbumSerializer(ClearUploadedImagesMixin, SlugFromTitleMixin, serializers.ModelSerializer):
    uploaded_image_fields = ("cover_image",)
    images = StaffGalleryImageSerializer(many=True, read_only=True)
    clear_cover_image = serializers.BooleanField(required=False, write_only=True)

    class Meta:
        model = GalleryAlbum
        fields = [
            "id",
            "slug",
            "title_en",
            "title_bn",
            "category",
            "description_en",
            "description_bn",
            "cover_image",
            "clear_cover_image",
            "cover_image_url",
            "order",
            "images",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}


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
