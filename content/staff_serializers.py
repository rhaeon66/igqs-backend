from django.utils.text import slugify
from rest_framework import serializers

from admissions.models import AdmissionFee, PaymentMethod

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


class StaffSiteSettingsSerializer(serializers.ModelSerializer):
    logo_src = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            "id",
            "school_name_en",
            "school_name_bn",
            "tagline_en",
            "tagline_bn",
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


class StaffHomeContentSerializer(serializers.ModelSerializer):
    class Meta:
        model = HomeContent
        fields = [
            "id",
            "hero_title_en",
            "hero_title_bn",
            "hero_subtitle_en",
            "hero_subtitle_bn",
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


class StaffLeaderSerializer(serializers.ModelSerializer):
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
            "photo_url",
            "order",
        ]


class StaffFacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = [
            "id",
            "title_en",
            "title_bn",
            "description_en",
            "description_bn",
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


class StaffEventSerializer(SlugFromTitleMixin, serializers.ModelSerializer):
    image_src = serializers.SerializerMethodField()

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
            "image_url",
            "image_src",
            "is_published",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffNewsSerializer(SlugFromTitleMixin, serializers.ModelSerializer):
    image_src = serializers.SerializerMethodField()

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
            "featured_image_url",
            "image_src",
            "published_at",
            "is_published",
            "is_important",
        ]
        extra_kwargs = {"slug": {"required": False, "allow_blank": True}}

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffGalleryImageSerializer(serializers.ModelSerializer):
    image_src = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = [
            "id",
            "album",
            "image_url",
            "image_src",
            "caption_en",
            "caption_bn",
            "order",
        ]

    def get_image_src(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class StaffGalleryAlbumSerializer(SlugFromTitleMixin, serializers.ModelSerializer):
    images = StaffGalleryImageSerializer(many=True, read_only=True)

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


class StaffPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            "id",
            "code",
            "name_en",
            "name_bn",
            "account_number",
            "account_name",
            "bank_name",
            "payment_type_en",
            "payment_type_bn",
            "instructions_en",
            "instructions_bn",
            "is_active",
            "order",
        ]
