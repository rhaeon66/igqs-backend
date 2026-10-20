from decimal import Decimal, InvalidOperation

from content.models import CurriculumGrade

from .models import AdmissionFee


def admission_grades():
    return CurriculumGrade.objects.filter(open_for_admission=True).order_by("order", "id")


def resolve_admission_grade(*, slug: str = "", name: str = ""):
    slug = (slug or "").strip().lower()
    name = (name or "").strip()
    grades = admission_grades()
    if slug:
        grade = grades.filter(slug=slug).first()
        if grade:
            return grade
    if not name:
        return None
    return (
        grades.filter(name_en__iexact=name).first()
        or grades.filter(name_bn__iexact=name).first()
    )


def fee_for_grade(grade):
    if grade:
        matched = AdmissionFee.objects.filter(
            is_active=True, grade=grade
        ).first()
        if matched:
            return matched
    return AdmissionFee.objects.filter(is_active=True, grade__isnull=True).first()


def expected_fee_amount(grade) -> Decimal | None:
    fee = fee_for_grade(grade)
    return fee.amount if fee else None


def parse_fee_amount(raw) -> Decimal | None:
    """Parse a staff-entered fee amount, or None to clear it. Raises ValueError."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        amount = Decimal(str(raw).strip())
    except InvalidOperation as exc:
        raise ValueError from exc
    if amount < 0 or amount > Decimal("99999999.99"):
        raise ValueError
    return amount.quantize(Decimal("0.01"))


def set_class_fee(grade, amount: Decimal | None) -> None:
    """Upsert the single active AdmissionFee for a grade (or the default
    fee when grade is None), keeping exactly one active row per grade."""
    existing = AdmissionFee.objects.filter(grade=grade).order_by("-is_active", "id")
    if amount is None:
        existing.filter(is_active=True).update(is_active=False)
        return
    fee = existing.first()
    if fee is None:
        fee = AdmissionFee.objects.create(
            grade=grade,
            amount=amount,
            currency="BDT",
            is_active=True,
        )
    else:
        fee.amount = amount
        fee.is_active = True
        fee.save(update_fields=["amount", "is_active"])
    existing.exclude(pk=fee.pk).filter(is_active=True).update(is_active=False)
