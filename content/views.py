from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AboutPage,
    CurriculumGrade,
    Event,
    Facility,
    GalleryAlbum,
    HomeContent,
    Leader,
    NewsPost,
    SiteSettings,
    WhyChooseItem,
)
from .serializers import (
    AboutPageSerializer,
    ContactMessageSerializer,
    CurriculumGradeSerializer,
    EventDetailSerializer,
    EventListSerializer,
    FacilitySerializer,
    GalleryAlbumSerializer,
    HomeContentSerializer,
    LeaderSerializer,
    NewsDetailSerializer,
    NewsListSerializer,
    SiteSettingsSerializer,
    WhyChooseSerializer,
)


def ctx(request):
    return {"request": request}


class SiteSettingsView(APIView):
    def get(self, request):
        obj = SiteSettings.objects.first()
        if not obj:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        return Response(SiteSettingsSerializer(obj, context=ctx(request)).data)


class HomeView(APIView):
    def get(self, request):
        home = HomeContent.objects.first()
        if not home:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        now = timezone.now()
        events = Event.objects.filter(is_published=True, start_at__gte=now)[:3]
        news = NewsPost.objects.filter(is_published=True)[:4]
        notices = NewsPost.objects.filter(is_published=True, is_important=True)[:5]
        gallery = GalleryAlbum.objects.prefetch_related("images")[:4]
        return Response(
            {
                "home": HomeContentSerializer(home, context=ctx(request)).data,
                "why_choose": WhyChooseSerializer(
                    WhyChooseItem.objects.all(), many=True, context=ctx(request)
                ).data,
                "upcoming_events": EventListSerializer(
                    events, many=True, context=ctx(request)
                ).data,
                "latest_news": NewsListSerializer(
                    news, many=True, context=ctx(request)
                ).data,
                "notices": NewsListSerializer(
                    notices, many=True, context=ctx(request)
                ).data,
                "gallery": GalleryAlbumSerializer(
                    gallery, many=True, context=ctx(request)
                ).data,
                "curriculum_highlights": CurriculumGradeSerializer(
                    CurriculumGrade.objects.all()[:4], many=True, context=ctx(request)
                ).data,
            }
        )


class AboutView(APIView):
    def get(self, request):
        about = AboutPage.objects.first()
        if not about:
            return Response({}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "about": AboutPageSerializer(about, context=ctx(request)).data,
                "leadership": LeaderSerializer(
                    Leader.objects.all(), many=True, context=ctx(request)
                ).data,
                "facilities": FacilitySerializer(
                    Facility.objects.all(), many=True, context=ctx(request)
                ).data,
            }
        )


class CurriculumView(APIView):
    def get(self, request):
        grades = CurriculumGrade.objects.prefetch_related("subjects", "documents")
        return Response(
            CurriculumGradeSerializer(grades, many=True, context=ctx(request)).data
        )


class EventListView(generics.ListAPIView):
    serializer_class = EventListSerializer

    def get_queryset(self):
        return Event.objects.filter(is_published=True)

    def list(self, request, *args, **kwargs):
        now = timezone.now()
        qs = self.get_queryset()
        upcoming = qs.filter(start_at__gte=now)
        previous = qs.filter(start_at__lt=now)
        return Response(
            {
                "upcoming": EventListSerializer(
                    upcoming, many=True, context=ctx(request)
                ).data,
                "previous": EventListSerializer(
                    previous, many=True, context=ctx(request)
                ).data,
            }
        )


class EventDetailView(generics.RetrieveAPIView):
    serializer_class = EventDetailSerializer
    lookup_field = "slug"
    queryset = Event.objects.filter(is_published=True)


class NewsListView(generics.ListAPIView):
    serializer_class = NewsListSerializer

    def get_queryset(self):
        qs = NewsPost.objects.filter(is_published=True)
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class NewsDetailView(generics.RetrieveAPIView):
    serializer_class = NewsDetailSerializer
    lookup_field = "slug"
    queryset = NewsPost.objects.filter(is_published=True)


class GalleryView(generics.ListAPIView):
    serializer_class = GalleryAlbumSerializer
    queryset = GalleryAlbum.objects.prefetch_related("images")

    def get_queryset(self):
        qs = super().get_queryset()
        category = self.request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return qs


class ContactCreateView(generics.CreateAPIView):
    serializer_class = ContactMessageSerializer
