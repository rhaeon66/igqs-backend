from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from admissions.models import AdmissionFee
from content.models import Event, HomeContent, NewsPost, SiteSettings, WhyChooseItem


class StaffContentTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="igqs", password="secret", is_staff=True
        )
        self.token = Token.objects.create(user=self.user)
        SiteSettings.objects.create(
            school_name_en="IGQS",
            school_name_bn="আইজিকিউএস",
            address_en="Uttara",
            address_bn="উত্তরা",
            phone_primary="01700000000",
            email="info@example.com",
            office_hours_en="9-4",
            office_hours_bn="৯-৪",
        )
        HomeContent.objects.create(
            hero_title_en="Old hero",
            hero_title_bn="পুরনো",
            hero_subtitle_en="Sub",
            hero_subtitle_bn="সাব",
            welcome_en="Welcome",
            welcome_bn="স্বাগতম",
            about_preview_en="About",
            about_preview_bn="সম্পর্কে",
            principal_name_en="Principal",
            principal_name_bn="অধ্যক্ষ",
            principal_title_en="Head",
            principal_title_bn="প্রধান",
            principal_message_en="Message",
            principal_message_bn="বার্তা",
        )

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_cms_requires_staff_auth(self):
        denied = self.client.get("/api/staff/home/")
        self.assertEqual(denied.status_code, 401)

    def test_update_home_and_public_api(self):
        self.auth()
        update = self.client.patch(
            "/api/staff/home/",
            {"hero_title_en": "New hero title", "hero_title_bn": "নতুন শিরোনাম"},
            format="json",
        )
        self.assertEqual(update.status_code, 200)
        self.assertEqual(update.data["hero_title_en"], "New hero title")

        public = self.client.get("/api/home/")
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data["home"]["hero_title"], "New hero title")

        public_bn = self.client.get("/api/home/?lang=bn")
        self.assertEqual(public_bn.data["home"]["hero_title"], "নতুন শিরোনাম")

    def test_create_why_choose_news_event_and_fee(self):
        self.auth()
        card = self.client.post(
            "/api/staff/why-choose/",
            {
                "title_en": "Care",
                "title_bn": "যত্ন",
                "description_en": "We care",
                "description_bn": "আমরা যত্ন করি",
                "icon": "heart",
                "order": 5,
            },
            format="json",
        )
        self.assertEqual(card.status_code, 201)
        self.assertEqual(WhyChooseItem.objects.count(), 1)

        news = self.client.post(
            "/api/staff/news/",
            {
                "title_en": "Holiday notice",
                "title_bn": "ছুটির নোটিশ",
                "category": "holiday",
                "description_en": "School closed Friday.",
                "description_bn": "শুক্রবার বন্ধ।",
                "published_at": "2026-09-06T10:00:00Z",
                "is_published": True,
                "is_important": True,
            },
            format="json",
        )
        self.assertEqual(news.status_code, 201)
        self.assertTrue(news.data["slug"])
        self.assertEqual(NewsPost.objects.get(pk=news.data["id"]).is_important, True)

        event = self.client.post(
            "/api/staff/events/",
            {
                "title_en": "Open day",
                "title_bn": "ওপেন ডে",
                "start_at": "2026-10-01T09:00:00Z",
                "location_en": "Campus",
                "location_bn": "ক্যাম্পাস",
                "description_en": "Visit us",
                "description_bn": "আসুন",
                "is_published": True,
            },
            format="json",
        )
        self.assertEqual(event.status_code, 201)
        self.assertTrue(Event.objects.filter(slug=event.data["slug"]).exists())

        fee = self.client.post(
            "/api/staff/fees/",
            {
                "amount": "16000.00",
                "currency": "BDT",
                "label_en": "Default fee",
                "label_bn": "সাধারণ ফি",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(fee.status_code, 201)
        self.assertEqual(AdmissionFee.objects.count(), 1)

        listed = self.client.get("/api/staff/news/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)

        deleted = self.client.delete(f"/api/staff/news/{news.data['id']}/")
        self.assertEqual(deleted.status_code, 204)
        self.assertEqual(NewsPost.objects.count(), 0)
