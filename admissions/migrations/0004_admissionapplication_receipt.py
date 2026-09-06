from django.db import migrations, models


def backfill_receipt_ids(apps, schema_editor):
    AdmissionApplication = apps.get_model("admissions", "AdmissionApplication")
    used = set(
        AdmissionApplication.objects.exclude(receipt_id="").values_list(
            "receipt_id", flat=True
        )
    )
    for application in AdmissionApplication.objects.filter(receipt_id=""):
        seq = application.application_id.rsplit("-", 1)[-1]
        candidate = f"IGQS-RC-{seq}"
        if candidate in used:
            number = 1
            while f"IGQS-RC-{number:05d}" in used:
                number += 1
            candidate = f"IGQS-RC-{number:05d}"
        application.receipt_id = candidate
        application.save(update_fields=["receipt_id"])
        used.add(candidate)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0003_admissionapplication_unique_admission_transaction_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="admissionapplication",
            name="receipt_id",
            field=models.CharField(blank=True, default="", editable=False, max_length=32),
        ),
        migrations.AddField(
            model_name="admissionapplication",
            name="receipt_pdf",
            field=models.FileField(blank=True, upload_to="admissions/receipts/"),
        ),
        migrations.AddField(
            model_name="admissionapplication",
            name="receipt_email_sent",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(backfill_receipt_ids, noop),
        migrations.AlterField(
            model_name="admissionapplication",
            name="receipt_id",
            field=models.CharField(editable=False, max_length=32, unique=True),
        ),
    ]
