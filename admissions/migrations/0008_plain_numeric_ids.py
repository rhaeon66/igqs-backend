from django.db import migrations


def _number_in(raw: str):
    text = (raw or "").strip()
    if text.isdigit():
        return int(text)
    tail = text.rsplit("-", 1)[-1]
    if tail.isdigit():
        return int(tail)
    return None


def to_plain_numbers(apps, schema_editor):
    AdmissionApplication = apps.get_model("admissions", "AdmissionApplication")
    rows = list(AdmissionApplication.objects.order_by("pk"))
    planned = []
    used_applications = set()
    used_receipts = set()
    for row in rows:
        application_number = _number_in(row.application_id)
        if application_number is None:
            application_number = 1
        while application_number in used_applications:
            application_number += 1
        used_applications.add(application_number)

        receipt_number = _number_in(row.receipt_id)
        if receipt_number is None:
            receipt_number = application_number
        while receipt_number in used_receipts:
            receipt_number += 1
        used_receipts.add(receipt_number)
        planned.append((row.pk, str(application_number), str(receipt_number)))

    for pk, _application_id, _receipt_id in planned:
        AdmissionApplication.objects.filter(pk=pk).update(
            application_id=f"tmp-{pk}",
            receipt_id=f"tmp-rc-{pk}",
        )
    for pk, application_id, receipt_id in planned:
        AdmissionApplication.objects.filter(pk=pk).update(
            application_id=application_id,
            receipt_id=receipt_id,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("admissions", "0007_payment_details"),
    ]

    operations = [
        migrations.RunPython(to_plain_numbers, migrations.RunPython.noop),
    ]
