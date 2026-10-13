from django.db import migrations, models


ADMISSION_CLASS_SLUGS = (
    "playgroup",
    "nursery",
    "kg",
    "class-1",
    "class-2",
    "class-3",
)


def mark_admission_classes(apps, schema_editor):
    CurriculumGrade = apps.get_model("content", "CurriculumGrade")
    CurriculumGrade.objects.filter(slug__in=ADMISSION_CLASS_SLUGS).update(
        open_for_admission=True
    )


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0002_image_uploads"),
    ]

    operations = [
        migrations.AddField(
            model_name="curriculumgrade",
            name="open_for_admission",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="curriculumgrade",
            name="listed_on_curriculum",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(mark_admission_classes, migrations.RunPython.noop),
    ]
