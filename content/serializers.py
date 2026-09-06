from rest_framework import serializers

from .models import (
    AboutPage,
    ContactMessage,
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


def lang_of(context) -> str:
    request = context.get("request")
    if request and request.query_params.get("lang") == "bn":
        return "bn"
    return "en"


def loc(obj, field: str, lang: str) -> str:
    return obj.localized(field, lang)


def abs_url(request, path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    if request:
        return request.build_absolute_uri(path)
    return path


class SiteSettingsSerializer(serializers.ModelSerializer):
    school_name = serializers.SerializerMethodField()
    tagline = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    office_hours = serializers.SerializerMethodField()
    admission_announcement = serializers.SerializerMethodField()
    logo = serializers.SerializerMethodField()

    class Meta:
        model = SiteSettings
        fields = [
            "school_name",
            "tagline",
            "logo",
            "address",
            "phone_primary",
            "phone_secondary",
            "email",
            "map_embed_url",
            "office_hours",
            "facebook_url",
            "youtube_url",
            "instagram_url",
            "whatsapp_url",
            "admission_open",
            "admission_announcement",
        ]

    def get_school_name(self, obj):
        return loc(obj, "school_name", lang_of(self.context))

    def get_tagline(self, obj):
        return loc(obj, "tagline", lang_of(self.context))

    def get_address(self, obj):
        return loc(obj, "address", lang_of(self.context))

    def get_office_hours(self, obj):
        return loc(obj, "office_hours", lang_of(self.context))

    def get_admission_announcement(self, obj):
        return loc(obj, "admission_announcement", lang_of(self.context))

    def get_logo(self, obj):
        return abs_url(self.context.get("request"), obj.logo_src)


class HomeContentSerializer(serializers.ModelSerializer):
    hero_title = serializers.SerializerMethodField()
    hero_subtitle = serializers.SerializerMethodField()
    welcome = serializers.SerializerMethodField()
    about_preview = serializers.SerializerMethodField()
    principal_name = serializers.SerializerMethodField()
    principal_title = serializers.SerializerMethodField()
    principal_message = serializers.SerializerMethodField()

    class Meta:
        model = HomeContent
        fields = [
            "hero_title",
            "hero_subtitle",
            "hero_image_url",
            "welcome",
            "about_preview",
            "principal_name",
            "principal_title",
            "principal_message",
            "principal_photo_url",
        ]

    def get_hero_title(self, obj):
        return loc(obj, "hero_title", lang_of(self.context))

    def get_hero_subtitle(self, obj):
        return loc(obj, "hero_subtitle", lang_of(self.context))

    def get_welcome(self, obj):
        return loc(obj, "welcome", lang_of(self.context))

    def get_about_preview(self, obj):
        return loc(obj, "about_preview", lang_of(self.context))

    def get_principal_name(self, obj):
        return loc(obj, "principal_name", lang_of(self.context))

    def get_principal_title(self, obj):
        return loc(obj, "principal_title", lang_of(self.context))

    def get_principal_message(self, obj):
        return loc(obj, "principal_message", lang_of(self.context))


class WhyChooseSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = WhyChooseItem
        fields = ["id", "title", "description", "icon"]

    def get_title(self, obj):
        return loc(obj, "title", lang_of(self.context))

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class AboutPageSerializer(serializers.ModelSerializer):
    introduction = serializers.SerializerMethodField()
    vision = serializers.SerializerMethodField()
    mission = serializers.SerializerMethodField()
    history = serializers.SerializerMethodField()
    quranic_approach = serializers.SerializerMethodField()
    principal_message = serializers.SerializerMethodField()

    class Meta:
        model = AboutPage
        fields = [
            "introduction",
            "vision",
            "mission",
            "history",
            "quranic_approach",
            "principal_message",
        ]

    def get_introduction(self, obj):
        return loc(obj, "introduction", lang_of(self.context))

    def get_vision(self, obj):
        return loc(obj, "vision", lang_of(self.context))

    def get_mission(self, obj):
        return loc(obj, "mission", lang_of(self.context))

    def get_history(self, obj):
        return loc(obj, "history", lang_of(self.context))

    def get_quranic_approach(self, obj):
        return loc(obj, "quranic_approach", lang_of(self.context))

    def get_principal_message(self, obj):
        return loc(obj, "principal_message", lang_of(self.context))


class LeaderSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    bio = serializers.SerializerMethodField()

    class Meta:
        model = Leader
        fields = ["id", "name", "role", "bio", "photo_url"]

    def get_name(self, obj):
        return loc(obj, "name", lang_of(self.context))

    def get_role(self, obj):
        return loc(obj, "role", lang_of(self.context))

    def get_bio(self, obj):
        return loc(obj, "bio", lang_of(self.context))


class FacilitySerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Facility
        fields = ["id", "title", "description", "image_url"]

    def get_title(self, obj):
        return loc(obj, "title", lang_of(self.context))

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class SubjectSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "name", "category", "description"]

    def get_name(self, obj):
        return loc(obj, "name", lang_of(self.context))

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class CurriculumDocumentSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = CurriculumDocument
        fields = ["id", "title", "download_url"]

    def get_title(self, obj):
        return loc(obj, "title", lang_of(self.context))

    def get_download_url(self, obj):
        return abs_url(self.context.get("request"), obj.download_url)


class CurriculumGradeSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    subjects = SubjectSerializer(many=True, read_only=True)
    documents = CurriculumDocumentSerializer(many=True, read_only=True)

    class Meta:
        model = CurriculumGrade
        fields = ["id", "slug", "name", "description", "subjects", "documents"]

    def get_name(self, obj):
        return loc(obj, "name", lang_of(self.context))

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class EventListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = ["slug", "title", "start_at", "end_at", "location", "image"]

    def get_title(self, obj):
        return loc(obj, "title", lang_of(self.context))

    def get_location(self, obj):
        return loc(obj, "location", lang_of(self.context))

    def get_image(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class EventDetailSerializer(EventListSerializer):
    description = serializers.SerializerMethodField()

    class Meta(EventListSerializer.Meta):
        fields = EventListSerializer.Meta.fields + ["description"]

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class NewsListSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = NewsPost
        fields = ["slug", "title", "category", "published_at", "image", "is_important"]

    def get_title(self, obj):
        return loc(obj, "title", lang_of(self.context))

    def get_image(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class NewsDetailSerializer(NewsListSerializer):
    description = serializers.SerializerMethodField()

    class Meta(NewsListSerializer.Meta):
        fields = NewsListSerializer.Meta.fields + ["description"]

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class GalleryImageSerializer(serializers.ModelSerializer):
    caption = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = ["id", "image", "caption"]

    def get_caption(self, obj):
        return loc(obj, "caption", lang_of(self.context))

    def get_image(self, obj):
        return abs_url(self.context.get("request"), obj.image_src)


class GalleryAlbumSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    images = GalleryImageSerializer(many=True, read_only=True)

    class Meta:
        model = GalleryAlbum
        fields = ["slug", "title", "category", "description", "cover_image_url", "images"]

    def get_title(self, obj):
        return loc(obj, "title", lang_of(self.context))

    def get_description(self, obj):
        return loc(obj, "description", lang_of(self.context))


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message"]
