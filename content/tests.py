from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, get_commands
from django.test import TestCase
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from admissions.models import AdmissionFee
from content.models import Event, GalleryAlbum, GalleryImage, HomeContent, NewsPost, SiteSettings, WhyChooseItem


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
        self.assertEqual(public.data["home"]["hero_title"], "নতুন শিরোনাম")

        public_en = self.client.get("/api/home/?lang=en")
        self.assertEqual(public_en.data["home"]["hero_title"], "New hero title")

    def test_home_keeps_image_url_and_upload(self):
        self.auth()
        buffer = BytesIO()
        Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
        upload = SimpleUploadedFile("hero.png", buffer.getvalue(), content_type="image/png")
        updated = self.client.patch(
            "/api/staff/home/",
            {"hero_image": upload, "hero_image_url": "https://example.com/hero.jpg"},
            format="multipart",
        )
        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertIn("/media/", updated.data["hero_image"])
        self.assertEqual(updated.data["hero_image_url"], "")

        public = self.client.get("/api/home/?lang=en")
        self.assertIn("/media/", public.data["home"]["hero_image_url"])

        ignored = self.client.patch(
            "/api/staff/home/",
            {"hero_image_url": ""},
            format="json",
        )
        self.assertEqual(ignored.status_code, 200, ignored.content)
        self.assertIn("/media/", ignored.data["hero_image"])

        cleared = self.client.patch(
            "/api/staff/home/",
            {"clear_hero_image": True, "hero_image_url": ""},
            format="json",
        )
        self.assertEqual(cleared.status_code, 200, cleared.content)
        self.assertIsNone(cleared.data["hero_image"])
        public = self.client.get("/api/home/?lang=en")
        self.assertEqual(public.data["home"]["hero_image_url"], "")

    def test_home_highlight_is_editable_and_public(self):
        self.auth()
        created = self.client.post(
            "/api/staff/highlights/",
            {
                "value": "12+",
                "label_en": "New campuses",
                "label_bn": "নতুন ক্যাম্পাস",
                "icon": "users",
                "order": 9,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201)

        public = self.client.get("/api/home/")
        added = next(item for item in public.data["highlights"] if item["value"] == "12+")
        self.assertEqual(added["label"], "নতুন ক্যাম্পাস")

        public_en = self.client.get("/api/home/?lang=en")
        added_en = next(item for item in public_en.data["highlights"] if item["value"] == "12+")
        self.assertEqual(added_en["label"], "New campuses")

    def test_testimonial_photo_is_public(self):
        self.auth()
        created = self.client.post(
            "/api/staff/testimonials/",
            {
                "name_en": "Test Guardian",
                "name_bn": "পরীক্ষার অভিভাবক",
                "role": "guardian",
                "quote_en": "The teachers are kind.",
                "quote_bn": "শিক্ষকরা স্নেহশীল।",
                "rating": 5,
                "order": 9,
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)

        buffer = BytesIO()
        Image.new("RGB", (8, 8), "blue").save(buffer, format="PNG")
        upload = SimpleUploadedFile("face.png", buffer.getvalue(), content_type="image/png")
        with_photo = self.client.patch(
            f"/api/staff/testimonials/{created.data['id']}/",
            {"image": upload},
            format="multipart",
        )
        self.assertEqual(with_photo.status_code, 200, with_photo.content)
        self.assertIn("/media/", with_photo.data["image"])

        public = self.client.get("/api/home/?lang=en")
        shown = next(item for item in public.data["testimonials"] if item["name"] == "Test Guardian")
        self.assertEqual(shown["role"], "guardian")
        self.assertIn("/media/", shown["image"])

        public_bn = self.client.get("/api/home/")
        shown_bn = next(item for item in public_bn.data["testimonials"] if item["quote"] == "শিক্ষকরা স্নেহশীল।")
        self.assertEqual(shown_bn["name"], "পরীক্ষার অভিভাবক")

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

        buffer = BytesIO()
        Image.new("RGB", (8, 8), "green").save(buffer, format="PNG")
        upload = SimpleUploadedFile("why.png", buffer.getvalue(), content_type="image/png")
        with_photo = self.client.patch(
            f"/api/staff/why-choose/{card.data['id']}/",
            {"image": upload},
            format="multipart",
        )
        self.assertEqual(with_photo.status_code, 200, with_photo.content)
        self.assertIn("/media/", with_photo.data["image"])
        public = self.client.get("/api/home/?lang=en")
        shown = next(item for item in public.data["why_choose"] if item["title"] == "Care")
        self.assertIn("/media/", shown["image"])

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
        notices = self.client.get("/api/news/?important=1&lang=en")
        self.assertEqual(notices.status_code, 200)
        self.assertEqual([item["title"] for item in notices.data], ["Holiday notice"])
        self.assertEqual(notices.data[0]["category"], "holiday")

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

    def test_payment_method_details_are_custom(self):
        self.auth()
        created = self.client.post(
            "/api/staff/methods/",
            {
                "name_en": "Upay",
                "name_bn": "উপায়",
                "is_active": True,
                "order": 1,
                "details": [
                    {
                        "label_en": "Number",
                        "label_bn": "নম্বর",
                        "value_en": "01711000999",
                        "value_bn": "01711000999",
                    },
                    {
                        "label_en": "Branch",
                        "label_bn": "শাখা",
                        "value_en": "Uttara",
                        "value_bn": "উত্তরা",
                    },
                ],
            },
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.content)
        self.assertEqual(created.data["code"], "upay")
        self.assertEqual(len(created.data["details"]), 2)

        public = self.client.get("/api/admissions/info/?lang=en")
        method = next(row for row in public.data["methods"] if row["code"] == "upay")
        self.assertEqual(method["details"][1]["label"], "Branch")
        self.assertEqual(method["details"][1]["value"], "Uttara")

    def _png(self, name):
        buffer = BytesIO()
        Image.new("RGB", (8, 8), "green").save(buffer, format="PNG")
        return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")

    def test_bulk_upload_gallery_images(self):
        self.auth()
        album = GalleryAlbum.objects.create(
            slug="campus-day",
            title_en="Campus day",
            title_bn="ক্যাম্পাস দিবস",
            category="campus",
        )
        GalleryImage.objects.create(album=album, order=4)
        response = self.client.post(
            "/api/staff/images/bulk/",
            {
                "album": album.id,
                "images": [self._png("one.png"), self._png("two.png")],
            },
            format="multipart",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(len(response.data), 2)
        orders = list(album.images.order_by("order").values_list("order", flat=True))
        self.assertEqual(orders, [4, 5, 6])

        rejected = self.client.post(
            "/api/staff/images/bulk/",
            {
                "album": album.id,
                "images": SimpleUploadedFile("notes.txt", b"not-an-image", content_type="text/plain"),
            },
            format="multipart",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(album.images.count(), 3)


class CreateSuTests(TestCase):
    def test_createsu_is_registered(self):
        self.assertIn("createsu", get_commands())

    def test_creates_superuser_from_env(self):
        User = get_user_model()
        env = {
            "DJANGO_SUPERUSER_USERNAME": "deployadmin",
            "DJANGO_SUPERUSER_PASSWORD": "pass@123",
            "DJANGO_SUPERUSER_EMAIL": "admin@igqs.edu.bd",
        }
        with patch.dict("os.environ", env, clear=False):
            call_command("createsu")
        user = User.objects.get(username="deployadmin")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password("pass@123"))

    def test_skips_when_password_missing(self):
        User = get_user_model()
        env = {
            "DJANGO_SUPERUSER_USERNAME": "orphan",
            "DJANGO_SUPERUSER_PASSWORD": "",
            "STAFF_USERNAME": "",
            "STAFF_PASSWORD": "",
        }
        with patch.dict("os.environ", env, clear=False):
            call_command("createsu")
        self.assertFalse(User.objects.filter(username="orphan").exists())
