from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("admissions", "0009_remove_phone_otp_and_guardian_session"),
    ]

    operations = [
        migrations.AddField(
            model_name="admissionapplication",
            name="guardian_nid",
            field=models.FileField(blank=True, upload_to="admissions/guardian-nids/"),
        ),
        migrations.AddField(
            model_name="admissionapplication",
            name="guardian_photo",
            field=models.ImageField(blank=True, upload_to="admissions/guardian-photos/"),
        ),
        migrations.AddField(
            model_name="admissionapplication",
            name="academic_documents",
            field=models.FileField(blank=True, upload_to="admissions/academic-documents/"),
        ),
    ]
