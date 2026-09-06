from io import BytesIO

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from PIL import Image
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from admissions.models import AdmissionApplication, ApplicationStatus, PaymentMethod, PaymentMethodCode
from admissions.receipts import build_receipt_pdf, issue_receipt


def image_upload(name="photo.png"):
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "green").save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def make_application(**overrides):
    fields = {
        "student_name": "Ayesha Karim",
        "student_name_bn": "আয়েশা করিম",
        "date_of_birth": "2018-04-12",
        "gender": "female",
        "birth_certificate": SimpleUploadedFile(
            "birth.pdf", b"%PDF-1.4 test", content_type="application/pdf"
        ),
        "applying_class": "Playgroup",
        "student_photo": image_upload(),
        "student_address": "Uttara, Dhaka",
        "father_name": "Karim Uddin",
        "mother_name": "Salma Begum",
        "guardian_name": "Karim Uddin",
        "father_occupation": "Teacher",
        "mobile": "01711000111",
        "email": "guardian@example.com",
        "guardian_address": "Uttara, Dhaka",
        "emergency_contact": "01711000222",
        "payment_method": PaymentMethodCode.BKASH,
        "transaction_id": overrides.pop("transaction_id", "TXNTEST001"),
        "payment_amount": 12000,
        "payment_date": timezone.localdate(),
        "payer_mobile": "01711000111",
    }
    fields.update(overrides)
    return AdmissionApplication.objects.create(**fields)


class ReceiptIdTests(TestCase):
    def test_application_and_receipt_ids_share_sequence(self):
        first = make_application(transaction_id="TXN-A")
        year = timezone.localdate().year
        self.assertEqual(first.application_id, f"IGQS-{year}-00001")
        self.assertEqual(first.receipt_id, "IGQS-RC-00001")

        second = make_application(transaction_id="TXN-B")
        self.assertEqual(second.application_id, f"IGQS-{year}-00002")
        self.assertEqual(second.receipt_id, "IGQS-RC-00002")


class ReceiptDocumentTests(TestCase):
    def test_pdf_contains_required_fields(self):
        application = make_application()
        pdf = build_receipt_pdf(application)
        self.assertTrue(pdf.startswith(b"%PDF"))
        self.assertGreater(len(pdf), 4000)
        self.assertIn(b"ReportLab", pdf)

    def test_issue_receipt_emails_pdf(self):
        application = make_application()
        issue_receipt(application, send_email=True)
        application.refresh_from_db()
        self.assertTrue(application.receipt_pdf)
        self.assertTrue(application.receipt_email_sent)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.subject, "IGQS Admission Application Receipt")
        self.assertEqual(message.to, ["guardian@example.com"])
        self.assertIn(application.application_id, message.body)
        self.assertIn(application.receipt_id, message.body)
        self.assertEqual(len(message.attachments), 1)
        self.assertTrue(message.attachments[0][0].endswith(".pdf"))


class AdmissionReceiptApiTests(APITestCase):
    def setUp(self):
        PaymentMethod.objects.create(
            code=PaymentMethodCode.BKASH,
            name_en="bKash",
            name_bn="বিকাশ",
            account_number="01711000111",
            payment_type_en="Send Money",
            payment_type_bn="সেন্ড মানি",
            instructions_en="Pay first.",
            instructions_bn="আগে পরিশোধ করুন।",
            is_active=True,
        )

    def test_apply_returns_receipt_and_download(self):
        payload = {
            "student_name": "Ayesha Karim",
            "student_name_bn": "আয়েশা করিম",
            "date_of_birth": "2018-04-12",
            "gender": "female",
            "birth_certificate": SimpleUploadedFile(
                "birth.pdf", b"%PDF-1.4 test", content_type="application/pdf"
            ),
            "applying_class": "Playgroup",
            "student_photo": image_upload(),
            "student_address": "Uttara, Dhaka",
            "father_name": "Karim Uddin",
            "mother_name": "Salma Begum",
            "guardian_name": "Karim Uddin",
            "father_occupation": "Teacher",
            "mobile": "01711000111",
            "email": "guardian@example.com",
            "guardian_address": "Uttara, Dhaka",
            "emergency_contact": "01711000222",
            "payment_method": "bkash",
            "transaction_id": "TXNAPI001",
            "payment_amount": "12000",
            "payment_date": str(timezone.localdate()),
            "payer_mobile": "01711000111",
        }
        response = self.client.post("/api/admissions/apply/", payload, format="multipart")
        self.assertEqual(response.status_code, 201, response.content)
        year = timezone.localdate().year
        self.assertEqual(response.data["application_id"], f"IGQS-{year}-00001")
        self.assertEqual(response.data["receipt_id"], "IGQS-RC-00001")
        self.assertTrue(response.data["receipt_email_sent"])
        self.assertIn("/receipts/IGQS-RC-00001/pdf/", response.data["receipt_pdf_url"])

        download = self.client.get(
            f"/api/admissions/applications/{response.data['application_id']}/receipt/"
        )
        self.assertEqual(download.status_code, 200)
        self.assertEqual(download["Content-Type"], "application/pdf")
        self.assertIn("IGQS-RC-00001.pdf", download["Content-Disposition"])

    def test_lookup_receipt_by_id(self):
        payload = {
            "student_name": "Ayesha Karim",
            "student_name_bn": "আয়েশা করিম",
            "date_of_birth": "2018-04-12",
            "gender": "female",
            "birth_certificate": SimpleUploadedFile(
                "birth.pdf", b"%PDF-1.4 test", content_type="application/pdf"
            ),
            "applying_class": "Playgroup",
            "student_photo": image_upload(),
            "student_address": "Uttara, Dhaka",
            "father_name": "Karim Uddin",
            "mother_name": "Salma Begum",
            "guardian_name": "Karim Uddin",
            "father_occupation": "Teacher",
            "mobile": "01711000111",
            "email": "guardian@example.com",
            "guardian_address": "Uttara, Dhaka",
            "emergency_contact": "01711000222",
            "payment_method": "bkash",
            "transaction_id": "TXNLOOKUP001",
            "payment_amount": "12000",
            "payment_date": str(timezone.localdate()),
            "payer_mobile": "01711000111",
        }
        created = self.client.post("/api/admissions/apply/", payload, format="multipart")
        self.assertEqual(created.status_code, 201, created.content)
        receipt_id = created.data["receipt_id"]

        missing = self.client.get("/api/admissions/receipts/IGQS-RC-99999/")
        self.assertEqual(missing.status_code, 404)

        found = self.client.get(f"/api/admissions/receipts/{receipt_id.lower()}/")
        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.data["receipt_id"], receipt_id)
        self.assertIn("/pdf/", found.data["receipt_pdf_url"])
        self.assertIn("inline=1", found.data["receipt_view_url"])

        pdf = self.client.get(f"/api/admissions/receipts/{receipt_id}/pdf/")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertIn("attachment", pdf["Content-Disposition"])

        inline = self.client.get(f"/api/admissions/receipts/{receipt_id}/pdf/?inline=1")
        self.assertEqual(inline.status_code, 200)
        self.assertIn("inline", inline["Content-Disposition"])


class StaffAdmissionTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(
            username="igqs", password="secret", is_staff=True
        )
        self.token = Token.objects.create(user=self.user)
        self.app = make_application(transaction_id="TXNSTAFF001")

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    def test_login_and_stats(self):
        denied = self.client.get("/api/admissions/staff/stats/")
        self.assertEqual(denied.status_code, 401)

        login = self.client.post(
            "/api/admissions/staff/login/",
            {"username": "igqs", "password": "secret"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.data["token"])

        self.auth()
        stats = self.client.get("/api/admissions/staff/stats/")
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.data["total"], 1)
        self.assertEqual(stats.data["pending"], 1)
        self.assertEqual(stats.data["today"], 1)

    def test_search_filter_and_approve_reject(self):
        self.auth()
        listed = self.client.get("/api/admissions/staff/applications/?q=Ayesha")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data["count"], 1)

        detail = self.client.get(
            f"/api/admissions/staff/applications/{self.app.application_id}/"
        )
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["payment_amount"], "12000.00")
        self.assertEqual(detail.data["transaction_id"], "TXNSTAFF001")
        self.assertTrue(detail.data["payment_method_label"])

        missing = self.client.get("/api/admissions/staff/applications/?q=NoSuchName")
        self.assertEqual(missing.data["count"], 0)

        reject = self.client.post(
            f"/api/admissions/staff/applications/{self.app.application_id}/status/",
            {"status": "rejected"},
            format="json",
        )
        self.assertEqual(reject.status_code, 400)

        reject = self.client.post(
            f"/api/admissions/staff/applications/{self.app.application_id}/status/",
            {"status": "rejected", "rejection_reason": "Transaction could not be verified."},
            format="json",
        )
        self.assertEqual(reject.status_code, 200)
        self.assertEqual(reject.data["status"], ApplicationStatus.REJECTED)

        public = self.client.get(
            f"/api/admissions/applications/{self.app.application_id}/"
        )
        self.assertEqual(public.status_code, 200)
        self.assertEqual(public.data["status"], ApplicationStatus.REJECTED)
        self.assertEqual(
            public.data["rejection_reason"],
            "Transaction could not be verified.",
        )

        by_app = self.client.get(
            f"/api/admissions/lookup/?q={self.app.application_id.lower()}"
        )
        self.assertEqual(by_app.status_code, 200)
        self.assertEqual(by_app.data["status"], ApplicationStatus.REJECTED)

        by_receipt = self.client.get(
            f"/api/admissions/lookup/?q={self.app.receipt_id}"
        )
        self.assertEqual(by_receipt.status_code, 200)
        self.assertEqual(by_receipt.data["application_id"], self.app.application_id)

        self.assertGreaterEqual(len(mail.outbox), 1)
        self.assertIn("Rejected", mail.outbox[-1].subject)
        self.assertIn("Transaction could not be verified.", mail.outbox[-1].body)

        pdf = self.client.get(
            f"/api/admissions/receipts/{self.app.receipt_id}/pdf/"
        )
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")

        approve = self.client.post(
            f"/api/admissions/staff/applications/{self.app.application_id}/status/",
            {"status": "approved"},
            format="json",
        )
        self.assertEqual(approve.status_code, 200)
        self.assertEqual(approve.data["status"], ApplicationStatus.APPROVED)
        self.assertEqual(approve.data["rejection_reason"], "")

        export = self.client.get("/api/admissions/staff/applications/export/")
        self.assertEqual(export.status_code, 200)
        self.assertIn("text/csv", export["Content-Type"])
        self.assertIn(self.app.application_id, export.content.decode())
