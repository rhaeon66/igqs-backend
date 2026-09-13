from decimal import Decimal

from content.models import CurriculumGrade

from .models import AdmissionFee

ADMISSION_CLASS_SLUGS = (
    "playgroup",
    "nursery",
    "kg",
    "class-1",
    "class-2",
    "class-3",
)


def admission_grades():
    return CurriculumGrade.objects.filter(slug__in=ADMISSION_CLASS_SLUGS)


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
