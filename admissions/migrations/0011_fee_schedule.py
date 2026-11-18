from django.db import migrations, models


BANGLA = [
    ("Pre-play", "প্রি-প্লে", 5000, 4500, 1400, None, "playgroup"),
    ("Play", "প্লে", 5000, 4550, 1450, None, "play"),
    ("Nursery", "নার্সারি", 5000, 4600, 1750, None, "nursery"),
    ("KG", "কেজি", 5000, 4650, 1950, 800, "kindergarten"),
    ("First", "প্রথম শ্রেণি", 5000, 4700, 2150, 900, "class-1"),
    ("Second", "দ্বিতীয় শ্রেণি", 5000, 4750, 2350, 1000, "class-2"),
    ("Third", "তৃতীয় শ্রেণি", 5000, 4800, 2550, 1050, "class-3"),
]

ENGLISH = [
    ("Standard Play", "স্ট্যান্ডার্ড প্লে", 6000, 5000, 2000, None),
    ("Standard Nursery", "স্ট্যান্ডার্ড নার্সারি", 7000, 5500, 2500, None),
    ("Standard KG", "স্ট্যান্ডার্ড কেজি", 7500, 6000, 2850, None),
    ("Standard One", "স্ট্যান্ডার্ড ওয়ান", 8000, 6500, 3150, None),
    ("Standard Two", "স্ট্যান্ডার্ড টু", 8500, 7000, 3500, None),
    ("Standard Three", "স্ট্যান্ডার্ড থ্রি", 9000, 7500, 3950, None),
]


def load_schedule(apps, schema_editor):
    FeeScheduleRow = apps.get_model("admissions", "FeeScheduleRow")
    AdmissionFee = apps.get_model("admissions", "AdmissionFee")
    Grade = apps.get_model("content", "CurriculumGrade")
    if FeeScheduleRow.objects.exists():
        return
    rows = []
    for order, (name_en, name_bn, admission, session, monthly, hifz, _slug) in enumerate(BANGLA, start=1):
        rows.append(
            FeeScheduleRow(
                track="bangla",
                name_en=name_en,
                name_bn=name_bn,
                admission_fee=admission,
                session_fee=session,
                monthly_fee=monthly,
                hifz_fee=hifz,
                order=order,
            )
        )
    for order, (name_en, name_bn, admission, session, monthly, hifz) in enumerate(ENGLISH, start=1):
        rows.append(
            FeeScheduleRow(
                track="english",
                name_en=name_en,
                name_bn=name_bn,
                admission_fee=admission,
                session_fee=session,
                monthly_fee=monthly,
                hifz_fee=hifz,
                order=order,
            )
        )
    FeeScheduleRow.objects.bulk_create(rows)

    for _name_en, _name_bn, admission, _session, _monthly, _hifz, slug in BANGLA:
        grade = Grade.objects.filter(slug=slug).first()
        if not grade:
            continue
        fee = AdmissionFee.objects.filter(grade=grade, is_active=True).first()
        if fee:
            fee.amount = admission
            fee.save(update_fields=["amount"])
        else:
            AdmissionFee.objects.create(
                grade=grade,
                amount=admission,
                currency="BDT",
                label_en="Admission Fee",
                label_bn="ভর্তি ফি",
                is_active=True,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0010_admission_required_documents"),
        ("content", "0012_leader_panel"),
    ]

    operations = [
        migrations.CreateModel(
            name="FeeScheduleRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("track", models.CharField(choices=[("bangla", "Bangla version"), ("english", "English version")], max_length=20)),
                ("name_en", models.CharField(max_length=80)),
                ("name_bn", models.CharField(max_length=80)),
                ("admission_fee", models.PositiveIntegerField()),
                ("session_fee", models.PositiveIntegerField()),
                ("monthly_fee", models.PositiveIntegerField()),
                ("hifz_fee", models.PositiveIntegerField(blank=True, null=True)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["track", "order", "id"]},
        ),
        migrations.RunPython(load_schedule, migrations.RunPython.noop),
    ]
