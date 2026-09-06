from django.contrib import admin

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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not SiteSettings.objects.exists()


@admin.register(HomeContent)
class HomeContentAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not HomeContent.objects.exists()


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not AboutPage.objects.exists()


@admin.register(WhyChooseItem)
class WhyChooseItemAdmin(admin.ModelAdmin):
    list_display = ("title_en", "order")


@admin.register(Leader)
class LeaderAdmin(admin.ModelAdmin):
    list_display = ("name_en", "role_en", "order")


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("title_en", "order")


class SubjectInline(admin.TabularInline):
    model = Subject
    extra = 0


class DocumentInline(admin.TabularInline):
    model = CurriculumDocument
    extra = 0


@admin.register(CurriculumGrade)
class CurriculumGradeAdmin(admin.ModelAdmin):
    list_display = ("name_en", "slug", "order")
    prepopulated_fields = {"slug": ("name_en",)}
    inlines = [SubjectInline, DocumentInline]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title_en", "start_at", "is_published")
    prepopulated_fields = {"slug": ("title_en",)}
    list_filter = ("is_published",)


@admin.register(NewsPost)
class NewsPostAdmin(admin.ModelAdmin):
    list_display = ("title_en", "category", "published_at", "is_important", "is_published")
    prepopulated_fields = {"slug": ("title_en",)}
    list_filter = ("category", "is_published", "is_important")


class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 0


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ("title_en", "category", "order")
    prepopulated_fields = {"slug": ("title_en",)}
    inlines = [GalleryImageInline]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("name", "subject", "email", "is_read", "created_at")
    list_filter = ("is_read",)
    readonly_fields = ("name", "email", "phone", "subject", "message", "created_at")
