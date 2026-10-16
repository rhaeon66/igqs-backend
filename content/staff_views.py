from django.db.models import Max
from PIL import Image, UnidentifiedImageError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from admissions.authentication import LocalStaffAuthentication
from admissions.models import AdmissionFee, PaymentMethod
from admissions.permissions import IsStaffUser

from .models import (
    STAT_ICONS,
    AboutPage,
    CurriculumDocument,
    CurriculumGrade,
    Event,
    Facility,
    GalleryAlbum,
    GalleryImage,
    HeroSlide,
    HomeContent,
    HomeStat,
    Leader,
    NewsPost,
    SiteSettings,
    Subject,
    Testimonial,
    WhyChooseItem,
)
from .staff_serializers import (
    StaffAboutPageSerializer,
    StaffAdmissionFeeSerializer,
    StaffCurriculumDocumentSerializer,
    StaffCurriculumGradeSerializer,
    StaffEventSerializer,
    StaffFacilitySerializer,
    StaffGalleryAlbumSerializer,
    StaffGalleryImageSerializer,
    StaffHeroSlideSerializer,
    StaffHomeContentSerializer,
    StaffHomeStatSerializer,
    StaffLeaderSerializer,
    StaffNewsSerializer,
    StaffPaymentMethodSerializer,
    StaffSiteSettingsSerializer,
    StaffSubjectSerializer,
    StaffTestimonialSerializer,
    StaffWhyChooseSerializer,
)


class StaffAuthMixin:
    authentication_classes = [LocalStaffAuthentication]
    permission_classes = [IsStaffUser]


class SingletonStaffView(StaffAuthMixin, APIView):
    model = None
    serializer_class = None

    def get_object(self):
        return self.model.objects.first() or self.model()

    def get(self, request):
        serializer = self.serializer_class(
            self.get_object(), context={"request": request}
        )
        return Response(serializer.data)

    def patch(self, request):
        instance = self.model.objects.first()
        serializer = self.serializer_class(
            instance,
            data=request.data,
            partial=bool(instance),
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class StaffSiteView(SingletonStaffView):
    model = SiteSettings
    serializer_class = StaffSiteSettingsSerializer


class StaffHomeView(SingletonStaffView):
    model = HomeContent
    serializer_class = StaffHomeContentSerializer


class StaffAboutView(SingletonStaffView):
    model = AboutPage
    serializer_class = StaffAboutPageSerializer


class StaffModelViewSet(StaffAuthMixin, viewsets.ModelViewSet):
    pass


class HeroSlideViewSet(StaffModelViewSet):
    queryset = HeroSlide.objects.all()
    serializer_class = StaffHeroSlideSerializer

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        uploads = request.FILES.getlist("images")
        if not uploads:
            return Response({"detail": "Choose at least one image."}, status=status.HTTP_400_BAD_REQUEST)
        if len(uploads) > 12:
            return Response({"detail": "Upload at most 12 images at a time."}, status=status.HTTP_400_BAD_REQUEST)
        for upload in uploads:
            content_type = str(getattr(upload, "content_type", ""))
            if content_type and not content_type.startswith("image/"):
                return Response({"detail": f"{upload.name} is not an image."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                Image.open(upload).verify()
            except (UnidentifiedImageError, OSError, ValueError):
                return Response({"detail": f"{upload.name} is not a valid image."}, status=status.HTTP_400_BAD_REQUEST)
            upload.seek(0)
        start = HeroSlide.objects.aggregate(max_order=Max("order"))["max_order"] or 0
        created = [
            HeroSlide.objects.create(image=upload, order=start + offset)
            for offset, upload in enumerate(uploads, start=1)
        ]
        return Response(
            self.get_serializer(created, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class HomeStatViewSet(StaffModelViewSet):
    queryset = HomeStat.objects.all()
    serializer_class = StaffHomeStatSerializer


class TestimonialViewSet(StaffModelViewSet):
    queryset = Testimonial.objects.all()
    serializer_class = StaffTestimonialSerializer


class WhyChooseViewSet(StaffModelViewSet):
    queryset = WhyChooseItem.objects.all()
    serializer_class = StaffWhyChooseSerializer


class LeaderViewSet(StaffModelViewSet):
    queryset = Leader.objects.all()
    serializer_class = StaffLeaderSerializer


class FacilityViewSet(StaffModelViewSet):
    queryset = Facility.objects.all()
    serializer_class = StaffFacilitySerializer


class CurriculumGradeViewSet(StaffModelViewSet):
    queryset = CurriculumGrade.objects.filter(listed_on_curriculum=True).prefetch_related(
        "subjects", "documents"
    )
    serializer_class = StaffCurriculumGradeSerializer


class SubjectViewSet(StaffModelViewSet):
    queryset = Subject.objects.select_related("grade")
    serializer_class = StaffSubjectSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        grade = self.request.query_params.get("grade")
        if grade:
            qs = qs.filter(grade_id=grade)
        return qs


class CurriculumDocumentViewSet(StaffModelViewSet):
    queryset = CurriculumDocument.objects.select_related("grade")
    serializer_class = StaffCurriculumDocumentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        grade = self.request.query_params.get("grade")
        if grade:
            qs = qs.filter(grade_id=grade)
        return qs


class EventViewSet(StaffModelViewSet):
    queryset = Event.objects.all()
    serializer_class = StaffEventSerializer


class NewsViewSet(StaffModelViewSet):
    queryset = NewsPost.objects.all()
    serializer_class = StaffNewsSerializer


class GalleryAlbumViewSet(StaffModelViewSet):
    queryset = GalleryAlbum.objects.prefetch_related("images")
    serializer_class = StaffGalleryAlbumSerializer


class GalleryImageViewSet(StaffModelViewSet):
    queryset = GalleryImage.objects.select_related("album")
    serializer_class = StaffGalleryImageSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        album = self.request.query_params.get("album")
        if album:
            qs = qs.filter(album_id=album)
        return qs

    @action(detail=False, methods=["post"], url_path="bulk")
    def bulk(self, request):
        album_id = request.data.get("album")
        uploads = request.FILES.getlist("images")
        if not album_id:
            return Response(
                {"detail": "Choose an album first."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not uploads:
            return Response(
                {"detail": "Choose at least one image."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(uploads) > 30:
            return Response(
                {"detail": "Upload at most 30 images at a time."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            album = GalleryAlbum.objects.get(pk=album_id)
        except (GalleryAlbum.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Album not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        for upload in uploads:
            content_type = str(getattr(upload, "content_type", ""))
            if content_type and not content_type.startswith("image/"):
                return Response(
                    {"detail": f"{upload.name} is not an image."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                Image.open(upload).verify()
            except (UnidentifiedImageError, OSError, ValueError):
                return Response(
                    {"detail": f"{upload.name} is not a valid image."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            upload.seek(0)

        start = (
            GalleryImage.objects.filter(album=album).aggregate(max_order=Max("order"))[
                "max_order"
            ]
            or 0
        )
        created = [
            GalleryImage.objects.create(album=album, image=upload, order=start + offset)
            for offset, upload in enumerate(uploads, start=1)
        ]
        serializer = self.get_serializer(created, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdmissionFeeViewSet(StaffModelViewSet):
    queryset = AdmissionFee.objects.select_related("grade")
    serializer_class = StaffAdmissionFeeSerializer


class PaymentMethodViewSet(StaffModelViewSet):
    queryset = PaymentMethod.objects.all()
    serializer_class = StaffPaymentMethodSerializer


class StaffCmsMetaView(StaffAuthMixin, APIView):
    def get(self, request):
        grades = CurriculumGrade.objects.order_by("order").values("id", "slug", "name_en")
        return Response(
            {
                "grades": list(grades),
                "subject_categories": [
                    {"value": "quranic", "label": "Qur'anic studies"},
                    {"value": "islamic", "label": "Islamic studies"},
                    {"value": "general", "label": "General education"},
                    {"value": "cocurricular", "label": "Co-curricular"},
                ],
                "news_categories": [
                    {"value": "news", "label": "News"},
                    {"value": "announcement", "label": "Announcement"},
                    {"value": "notice", "label": "Notice"},
                    {"value": "admission", "label": "Admission notice"},
                    {"value": "holiday", "label": "Holiday notice"},
                    {"value": "exam", "label": "Examination notice"},
                    {"value": "update", "label": "Important update"},
                ],
                "gallery_categories": [
                    {"value": "activities", "label": "School activities"},
                    {"value": "events", "label": "Events"},
                    {"value": "classroom", "label": "Classroom activities"},
                    {"value": "cultural", "label": "Cultural programs"},
                    {"value": "sports", "label": "Sports"},
                    {"value": "islamic", "label": "Islamic/Qur'anic activities"},
                    {"value": "campus", "label": "Campus photos"},
                ],
                "payment_codes": [
                    {"value": "bkash", "label": "bKash"},
                    {"value": "nagad", "label": "Nagad"},
                    {"value": "rocket", "label": "Rocket"},
                    {"value": "bank", "label": "Bank Transfer"},
                ],
                "why_icons": [
                    {"value": "book-open", "label": "Book"},
                    {"value": "layers", "label": "Layers"},
                    {"value": "heart", "label": "Heart"},
                    {"value": "shield", "label": "Shield"},
                ],
                "stat_icons": [{"value": value, "label": label} for value, label in STAT_ICONS],
            }
        )
