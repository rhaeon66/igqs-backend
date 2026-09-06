from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import staff_views, views

router = DefaultRouter()
router.register("staff/why-choose", staff_views.WhyChooseViewSet, basename="staff-why-choose")
router.register("staff/leaders", staff_views.LeaderViewSet, basename="staff-leaders")
router.register("staff/facilities", staff_views.FacilityViewSet, basename="staff-facilities")
router.register("staff/grades", staff_views.CurriculumGradeViewSet, basename="staff-grades")
router.register("staff/subjects", staff_views.SubjectViewSet, basename="staff-subjects")
router.register("staff/documents", staff_views.CurriculumDocumentViewSet, basename="staff-documents")
router.register("staff/events", staff_views.EventViewSet, basename="staff-events")
router.register("staff/news", staff_views.NewsViewSet, basename="staff-news")
router.register("staff/albums", staff_views.GalleryAlbumViewSet, basename="staff-albums")
router.register("staff/images", staff_views.GalleryImageViewSet, basename="staff-images")
router.register("staff/fees", staff_views.AdmissionFeeViewSet, basename="staff-fees")
router.register("staff/methods", staff_views.PaymentMethodViewSet, basename="staff-methods")

urlpatterns = [
    path("site/", views.SiteSettingsView.as_view()),
    path("home/", views.HomeView.as_view()),
    path("about/", views.AboutView.as_view()),
    path("curriculum/", views.CurriculumView.as_view()),
    path("events/", views.EventListView.as_view()),
    path("events/<slug:slug>/", views.EventDetailView.as_view()),
    path("news/", views.NewsListView.as_view()),
    path("news/<slug:slug>/", views.NewsDetailView.as_view()),
    path("gallery/", views.GalleryView.as_view()),
    path("contact/", views.ContactCreateView.as_view()),
    path("staff/site/", staff_views.StaffSiteView.as_view()),
    path("staff/home/", staff_views.StaffHomeView.as_view()),
    path("staff/about/", staff_views.StaffAboutView.as_view()),
    path("staff/meta/", staff_views.StaffCmsMetaView.as_view()),
    path("", include(router.urls)),
]
