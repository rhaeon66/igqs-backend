from django.urls import path

from . import staff_views, views

urlpatterns = [
    path("classes/", views.ApplyingClassListView.as_view()),
    path("info/", views.AdmissionInfoView.as_view()),
    path("apply/", views.AdmissionApplicationCreateView.as_view()),
    path("lookup/", views.AdmissionLookupView.as_view()),
    path("staff/login/", staff_views.StaffLoginView.as_view()),
    path("staff/logout/", staff_views.StaffLogoutView.as_view()),
    path("staff/me/", staff_views.StaffMeView.as_view()),
    path("staff/stats/", staff_views.StaffAdmissionStatsView.as_view()),
    path("staff/applications/export/", staff_views.StaffApplicationExportView.as_view()),
    path(
        "staff/applications/<str:application_id>/status/",
        staff_views.StaffApplicationStatusView.as_view(),
    ),
    path(
        "staff/applications/<str:application_id>/export/",
        staff_views.StaffApplicationExportView.as_view(),
    ),
    path(
        "staff/applications/<str:application_id>/receipt/",
        staff_views.StaffReceiptDownloadView.as_view(),
    ),
    path(
        "staff/applications/<str:application_id>/",
        staff_views.StaffApplicationDetailView.as_view(),
    ),
    path("staff/applications/", staff_views.StaffApplicationListView.as_view()),
    path(
        "receipts/<str:receipt_id>/pdf/",
        views.AdmissionReceiptPdfByIdView.as_view(),
    ),
    path(
        "receipts/<str:receipt_id>/",
        views.AdmissionReceiptLookupView.as_view(),
    ),
    path(
        "applications/<str:application_id>/receipt/",
        views.AdmissionReceiptDownloadView.as_view(),
    ),
    path(
        "applications/<str:application_id>/",
        views.AdmissionApplicationDetailView.as_view(),
    ),
]
