from django.db import models
from django.utils import timezone


class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"


class ApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending Verification"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"


class PaymentMethodCode(models.TextChoices):
    BKASH = "bkash", "bKash"
    NAGAD = "nagad", "Nagad"
    ROCKET = "rocket", "Rocket"
    BANK = "bank", "Bank Transfer"


class AdmissionFee(models.Model):
    grade = models.ForeignKey(
        "content.CurriculumGrade",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="admission_fees",
        help_text="Leave empty for the default fee shown to all applicants.",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=8, default="BDT")
    label_en = models.CharField(max_length=120, default="Admission Fee")
    label_bn = models.CharField(max_length=120, default="ভর্তি ফি")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["grade__order", "id"]

    def __str__(self) -> str:
        target = self.grade.name_en if self.grade else "Default"
        return f"{target}: {self.currency} {self.amount}"

    def display_amount(self) -> str:
        return f"{self.currency} {int(self.amount):,}"


class PaymentMethod(models.Model):
    code = models.CharField(max_length=20, choices=PaymentMethodCode.choices, unique=True)
    name_en = models.CharField(max_length=80)
    name_bn = models.CharField(max_length=80)
    account_number = models.CharField(max_length=80)
    account_name = models.CharField(max_length=120, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    payment_type_en = models.CharField(max_length=80)
    payment_type_bn = models.CharField(max_length=80)
    instructions_en = models.TextField()
    instructions_bn = models.TextField()
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self) -> str:
        return self.name_en

    def localized(self, field: str, lang: str) -> str:
        lang = "bn" if lang == "bn" else "en"
        value = getattr(self, f"{field}_{lang}", "") or ""
        if value:
            return value
        fallback = "en" if lang == "bn" else "bn"
        return getattr(self, f"{field}_{fallback}", "") or ""


class AdmissionApplication(models.Model):
    application_id = models.CharField(max_length=32, unique=True, editable=False)
    student_name = models.CharField(max_length=150)
    student_name_bn = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    birth_certificate = models.FileField(upload_to="admissions/birth-certificates/")
    previous_class = models.CharField(max_length=80, blank=True)
    applying_class = models.CharField(max_length=80)
    student_photo = models.ImageField(upload_to="admissions/photos/")
    student_address = models.TextField()
    father_name = models.CharField(max_length=150)
    mother_name = models.CharField(max_length=150)
    guardian_name = models.CharField(max_length=150)
    father_occupation = models.CharField(max_length=120)
    mother_occupation = models.CharField(max_length=120, blank=True)
    mobile = models.CharField(max_length=20)
    email = models.EmailField()
    guardian_address = models.TextField()
    emergency_contact = models.CharField(max_length=80)
    previous_academic_info = models.TextField(blank=True)
    special_requirements = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.PENDING,
    )
    payment_method = models.CharField(
        max_length=20, choices=PaymentMethodCode.choices, default=PaymentMethodCode.BKASH
    )
    transaction_id = models.CharField(max_length=80, default="")
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateField(default=timezone.localdate)
    payer_mobile = models.CharField(max_length=20, default="")
    payment_screenshot = models.ImageField(
        upload_to="admissions/payments/", blank=True
    )
    receipt_id = models.CharField(max_length=32, unique=True, editable=False)
    receipt_pdf = models.FileField(upload_to="admissions/receipts/", blank=True)
    receipt_email_sent = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_applications",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["transaction_id"],
                condition=~models.Q(transaction_id=""),
                name="unique_admission_transaction_id",
            )
        ]

    def __str__(self) -> str:
        return f"{self.application_id} — {self.student_name}"

    def transaction_data(self) -> dict:
        screenshot = self.payment_screenshot.url if self.payment_screenshot else ""
        return {
            "payment_method": self.payment_method,
            "transaction_id": self.transaction_id,
            "payment_amount": str(self.payment_amount),
            "payment_date": self.payment_date.isoformat() if self.payment_date else "",
            "payer_mobile": self.payer_mobile,
            "payment_screenshot": screenshot,
        }

    def save(self, *args, **kwargs):
        if not self.application_id:
            self.application_id, generated_receipt = self._next_ids()
            if not self.receipt_id:
                self.receipt_id = generated_receipt
        elif not self.receipt_id:
            self.receipt_id = self._receipt_id_for(self.application_id)
        super().save(*args, **kwargs)

    @classmethod
    def _next_ids(cls) -> tuple[str, str]:
        year = timezone.localdate().year
        prefix = f"IGQS-{year}-"
        last = (
            cls.objects.filter(application_id__startswith=prefix)
            .order_by("-application_id")
            .first()
        )
        next_number = 1
        if last:
            try:
                next_number = int(last.application_id.split("-")[-1]) + 1
            except ValueError:
                next_number = cls.objects.filter(application_id__startswith=prefix).count() + 1
        return f"{prefix}{next_number:05d}", cls._unique_receipt_id(next_number)

    @classmethod
    def _receipt_id_for(cls, application_id: str) -> str:
        try:
            number = int(application_id.rsplit("-", 1)[-1])
        except ValueError:
            number = cls.objects.count() + 1
        return cls._unique_receipt_id(number)

    @classmethod
    def _unique_receipt_id(cls, number: int) -> str:
        candidate = f"IGQS-RC-{number:05d}"
        while cls.objects.filter(receipt_id=candidate).exists():
            number += 1
            candidate = f"IGQS-RC-{number:05d}"
        return candidate
