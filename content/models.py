from django.db import models


class BilingualMixin:
    def localized(self, field: str, lang: str) -> str:
        lang = "bn" if lang == "bn" else "en"
        value = getattr(self, f"{field}_{lang}", "") or ""
        if value:
            return value
        fallback = "en" if lang == "bn" else "bn"
        return getattr(self, f"{field}_{fallback}", "") or ""


def public_image(instance, filename: str) -> str:
    return f"{instance._meta.model_name}/{filename}"


class SiteSettings(BilingualMixin, models.Model):
    school_name_en = models.CharField(max_length=200)
    school_name_bn = models.CharField(max_length=200)
    tagline_en = models.CharField(max_length=300, blank=True)
    tagline_bn = models.CharField(max_length=300, blank=True)
    logo = models.ImageField(upload_to="branding/", blank=True)
    logo_url = models.URLField(blank=True)
    address_en = models.CharField(max_length=400)
    address_bn = models.CharField(max_length=400)
    phone_primary = models.CharField(max_length=40)
    phone_secondary = models.CharField(max_length=40, blank=True)
    email = models.EmailField()
    map_embed_url = models.URLField(max_length=800, blank=True)
    office_hours_en = models.CharField(max_length=200)
    office_hours_bn = models.CharField(max_length=200)
    facebook_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    admission_open = models.BooleanField(default=True)
    admission_announcement_en = models.TextField(blank=True)
    admission_announcement_bn = models.TextField(blank=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def __str__(self) -> str:
        return self.school_name_en

    @property
    def logo_src(self) -> str:
        if self.logo:
            return self.logo.url
        return self.logo_url


class HomeContent(BilingualMixin, models.Model):
    hero_title_en = models.CharField(max_length=250)
    hero_title_bn = models.CharField(max_length=250)
    hero_subtitle_en = models.TextField()
    hero_subtitle_bn = models.TextField()
    hero_image = models.ImageField(upload_to="home/", blank=True)
    hero_image_url = models.URLField(blank=True)
    welcome_en = models.TextField()
    welcome_bn = models.TextField()
    about_preview_en = models.TextField()
    about_preview_bn = models.TextField()
    principal_name_en = models.CharField(max_length=120)
    principal_name_bn = models.CharField(max_length=120)
    principal_title_en = models.CharField(max_length=120)
    principal_title_bn = models.CharField(max_length=120)
    principal_message_en = models.TextField()
    principal_message_bn = models.TextField()
    principal_photo = models.ImageField(upload_to="home/", blank=True)
    principal_photo_url = models.URLField(blank=True)

    class Meta:
        verbose_name = "Home content"
        verbose_name_plural = "Home content"

    def __str__(self) -> str:
        return "Homepage content"

    @property
    def hero_image_src(self) -> str:
        if self.hero_image:
            return self.hero_image.url
        return self.hero_image_url

    @property
    def principal_photo_src(self) -> str:
        if self.principal_photo:
            return self.principal_photo.url
        return self.principal_photo_url


class HeroSlide(models.Model):
    image = models.ImageField(upload_to="home/slides/")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"Hero slide {self.pk}"


STAT_ICONS = (
    ("users", "Students"),
    ("graduation-cap", "Teachers"),
    ("award", "Award"),
    ("sparkles", "Experience"),
)


class HomeStat(BilingualMixin, models.Model):
    value = models.CharField(max_length=40)
    label_en = models.CharField(max_length=80)
    label_bn = models.CharField(max_length=80)
    icon = models.CharField(max_length=40, choices=STAT_ICONS, default="users")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return f"{self.value} {self.label_en}"


class WhyChooseItem(BilingualMixin, models.Model):
    title_en = models.CharField(max_length=150)
    title_bn = models.CharField(max_length=150)
    description_en = models.TextField()
    description_bn = models.TextField()
    icon = models.CharField(max_length=40, default="book")
    image = models.ImageField(upload_to="why/", blank=True)
    image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.title_en

    @property
    def image_src(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url


class Testimonial(BilingualMixin, models.Model):
    GUARDIAN = "guardian"
    STUDENT = "student"
    ROLE_CHOICES = (
        (GUARDIAN, "Guardian"),
        (STUDENT, "Student"),
    )

    name_en = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=GUARDIAN)
    quote_en = models.TextField()
    quote_bn = models.TextField()
    spoken_on = models.DateTimeField(null=True, blank=True)
    rating = models.PositiveSmallIntegerField(default=5)
    facebook_url = models.URLField(blank=True)
    image = models.ImageField(upload_to="testimonials/", blank=True)
    image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self) -> str:
        return self.name_en

    @property
    def image_src(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url


class AboutPage(BilingualMixin, models.Model):
    introduction_en = models.TextField()
    introduction_bn = models.TextField()
    vision_en = models.TextField()
    vision_bn = models.TextField()
    mission_en = models.TextField()
    mission_bn = models.TextField()
    history_en = models.TextField()
    history_bn = models.TextField()
    quranic_approach_en = models.TextField()
    quranic_approach_bn = models.TextField()
    principal_message_en = models.TextField()
    principal_message_bn = models.TextField()

    class Meta:
        verbose_name = "About page"
        verbose_name_plural = "About page"

    def __str__(self) -> str:
        return "About page"


class Leader(BilingualMixin, models.Model):
    name_en = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120)
    role_en = models.CharField(max_length=150)
    role_bn = models.CharField(max_length=150)
    bio_en = models.TextField(blank=True)
    bio_bn = models.TextField(blank=True)
    photo = models.ImageField(upload_to="leaders/", blank=True)
    photo_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name_en

    @property
    def photo_src(self) -> str:
        if self.photo:
            return self.photo.url
        return self.photo_url


class Facility(BilingualMixin, models.Model):
    title_en = models.CharField(max_length=150)
    title_bn = models.CharField(max_length=150)
    description_en = models.TextField()
    description_bn = models.TextField()
    image = models.ImageField(upload_to="facilities/", blank=True)
    image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]
        verbose_name_plural = "Facilities"

    def __str__(self) -> str:
        return self.title_en

    @property
    def image_src(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url


class CurriculumGrade(BilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    name_en = models.CharField(max_length=120)
    name_bn = models.CharField(max_length=120)
    description_en = models.TextField()
    description_bn = models.TextField()
    order = models.PositiveIntegerField(default=0)
    open_for_admission = models.BooleanField(default=False)
    listed_on_curriculum = models.BooleanField(default=True)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name_en

    @property
    def fee_amount(self) -> str:
        # This class's own admission fee only — deliberately NOT
        # admissions.eligibility.fee_for_grade(), which falls back to the
        # school-wide default fee when a class has none of its own. That
        # fallback is correct for "what does an applicant actually pay,"
        # but wrong here: the staff editor needs to show/edit this specific
        # class's fee, not silently display someone else's amount as if it
        # were this class's setting. Import is local to avoid a circular
        # import (admissions already imports CurriculumGrade from here).
        if not self.pk:
            return ""
        from admissions.models import AdmissionFee

        fee = AdmissionFee.objects.filter(grade=self, is_active=True).first()
        return str(fee.amount) if fee else ""


class SubjectCategory(models.TextChoices):
    QURANIC = "quranic", "Qur'anic studies"
    ISLAMIC = "islamic", "Islamic studies"
    GENERAL = "general", "General education"
    COCURRICULAR = "cocurricular", "Co-curricular"


class Subject(BilingualMixin, models.Model):
    grade = models.ForeignKey(
        CurriculumGrade, on_delete=models.CASCADE, related_name="subjects"
    )
    name_en = models.CharField(max_length=150)
    name_bn = models.CharField(max_length=150)
    category = models.CharField(max_length=20, choices=SubjectCategory.choices)
    description_en = models.TextField(blank=True)
    description_bn = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return f"{self.grade.name_en} — {self.name_en}"


class CurriculumDocument(BilingualMixin, models.Model):
    title_en = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200)
    file = models.FileField(upload_to="curriculum/", blank=True)
    file_url = models.URLField(blank=True)
    grade = models.ForeignKey(
        CurriculumGrade,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
    )
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.title_en

    @property
    def download_url(self) -> str:
        if self.file:
            return self.file.url
        return self.file_url


class Event(BilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    title_en = models.CharField(max_length=200)
    title_bn = models.CharField(max_length=200)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    location_en = models.CharField(max_length=200)
    location_bn = models.CharField(max_length=200)
    description_en = models.TextField()
    description_bn = models.TextField()
    image = models.ImageField(upload_to="events/", blank=True)
    image_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        ordering = ["-start_at"]

    def __str__(self) -> str:
        return self.title_en

    @property
    def image_src(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url


class NewsCategory(models.TextChoices):
    NEWS = "news", "News"
    ANNOUNCEMENT = "announcement", "Announcement"
    NOTICE = "notice", "Notice"
    ADMISSION = "admission", "Admission notice"
    HOLIDAY = "holiday", "Holiday notice"
    EXAM = "exam", "Examination notice"
    UPDATE = "update", "Important update"


class NewsPost(BilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    title_en = models.CharField(max_length=220)
    title_bn = models.CharField(max_length=220)
    category = models.CharField(max_length=20, choices=NewsCategory.choices)
    description_en = models.TextField()
    description_bn = models.TextField()
    featured_image = models.ImageField(upload_to="news/", blank=True)
    featured_image_url = models.URLField(blank=True)
    published_at = models.DateTimeField()
    is_published = models.BooleanField(default=True)
    is_important = models.BooleanField(default=False)

    class Meta:
        ordering = ["-published_at"]

    def __str__(self) -> str:
        return self.title_en

    @property
    def image_src(self) -> str:
        if self.featured_image:
            return self.featured_image.url
        return self.featured_image_url


class GalleryCategory(models.TextChoices):
    ACTIVITIES = "activities", "School activities"
    EVENTS = "events", "Events"
    CLASSROOM = "classroom", "Classroom activities"
    CULTURAL = "cultural", "Cultural programs"
    SPORTS = "sports", "Sports"
    ISLAMIC = "islamic", "Islamic/Qur'anic activities"
    CAMPUS = "campus", "Campus photos"


class GalleryAlbum(BilingualMixin, models.Model):
    slug = models.SlugField(unique=True)
    title_en = models.CharField(max_length=180)
    title_bn = models.CharField(max_length=180)
    category = models.CharField(max_length=20, choices=GalleryCategory.choices)
    description_en = models.TextField(blank=True)
    description_bn = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to="gallery/", blank=True)
    cover_image_url = models.URLField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "-id"]

    def __str__(self) -> str:
        return self.title_en

    @property
    def cover_image_src(self) -> str:
        if self.cover_image:
            return self.cover_image.url
        return self.cover_image_url


class GalleryImage(BilingualMixin, models.Model):
    album = models.ForeignKey(
        GalleryAlbum, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="gallery/", blank=True)
    image_url = models.URLField(blank=True)
    caption_en = models.CharField(max_length=200, blank=True)
    caption_bn = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.caption_en or f"Image {self.pk}"

    @property
    def image_src(self) -> str:
        if self.image:
            return self.image.url
        return self.image_url


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=40, blank=True)
    subject = models.CharField(max_length=180)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} — {self.subject}"
