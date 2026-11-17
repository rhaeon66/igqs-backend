from rest_framework import serializers

from content.api.public.serializers import abs_url
from content.api.staff.serializers.mixins import ClearUploadedImagesMixin, SanitizeHtmlMixin, SlugFromTitleMixin
from content.models import Event, GalleryAlbum, GalleryImage, NewsPost


class StaffEventSerializer(SanitizeHtmlMixin, ClearUploadedImagesMixin, SlugFromTitleMixin, serializers.ModelSerializer):
    html_fields = ("description_en", "description_bn")
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

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start = attrs.get("start_at", getattr(self.instance, "start_at", None))
        end = attrs["end_at"] if "end_at" in attrs else getattr(self.instance, "end_at", None)
        if start and end and end < start:
            raise serializers.ValidationError({"end_at": "The end must be after the start."})
        return attrs


class StaffNewsSerializer(SanitizeHtmlMixin, ClearUploadedImagesMixin, SlugFromTitleMixin, serializers.ModelSerializer):
    html_fields = ("description_en", "description_bn")
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
