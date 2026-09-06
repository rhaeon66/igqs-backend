from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.response import Response
from rest_framework.views import APIView

from admissions.models import AdmissionFee, PaymentMethod
from admissions.permissions import IsStaffUser

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
from .staff_serializers import (
    StaffAboutPageSerializer,
    StaffAdmissionFeeSerializer,
    StaffCurriculumDocumentSerializer,
    StaffCurriculumGradeSerializer,
    StaffEventSerializer,
    StaffFacilitySerializer,
    StaffGalleryAlbumSerializer,
    StaffGalleryImageSerializer,
    StaffHomeContentSerializer,
    StaffLeaderSerializer,
    StaffNewsSerializer,
    StaffPaymentMethodSerializer,
    StaffSiteSettingsSerializer,
    StaffSubjectSerializer,
    StaffWhyChooseSerializer,
)


class StaffAuthMixin:
    authentication_classes = [TokenAuthentication]
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
    queryset = CurriculumGrade.objects.prefetch_related("subjects", "documents")
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
            }
        )
