from django.db import migrations, models
import django.db.models.deletion


def copy_payment_details(apps, schema_editor):
    PaymentMethod = apps.get_model("admissions", "PaymentMethod")
    PaymentDetail = apps.get_model("admissions", "PaymentDetail")
    for method in PaymentMethod.objects.all():
        rows = []
        if method.account_number:
            rows.append(("Number", "নম্বর", method.account_number, method.account_number))
        if method.account_name:
            rows.append(("Account name", "অ্যাকাউন্টের নাম", method.account_name, method.account_name))
        if method.bank_name:
            rows.append(("Branch", "শাখা", method.bank_name, method.bank_name))
        if method.payment_type_en or method.payment_type_bn:
            rows.append(("Payment", "পেমেন্ট", method.payment_type_en, method.payment_type_bn))
        if method.instructions_en or method.instructions_bn:
            rows.append(("Note", "নোট", method.instructions_en, method.instructions_bn))
        PaymentDetail.objects.bulk_create(
            [
                PaymentDetail(
                    method=method,
                    label_en=label_en,
                    label_bn=label_bn,
                    value_en=value_en,
                    value_bn=value_bn,
                    order=index,
                )
                for index, (label_en, label_bn, value_en, value_bn) in enumerate(rows)
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0006_phone_otp_and_guardian_session"),
    ]

    operations = [
        migrations.AlterField(
            model_name="paymentmethod",
            name="account_number",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AlterField(
            model_name="paymentmethod",
            name="code",
            field=models.SlugField(max_length=20, unique=True),
        ),
        migrations.AlterField(
            model_name="paymentmethod",
            name="instructions_bn",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="paymentmethod",
            name="instructions_en",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="paymentmethod",
            name="payment_type_bn",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AlterField(
            model_name="paymentmethod",
            name="payment_type_en",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AlterField(
            model_name="admissionapplication",
            name="payment_method",
            field=models.CharField(default="", max_length=20),
        ),
        migrations.CreateModel(
            name="PaymentDetail",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("label_en", models.CharField(blank=True, max_length=120)),
                ("label_bn", models.CharField(blank=True, max_length=120)),
                ("value_en", models.TextField(blank=True)),
                ("value_bn", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
                (
                    "method",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="details",
                        to="admissions.paymentmethod",
                    ),
                ),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.RunPython(copy_payment_details, migrations.RunPython.noop),
    ]
