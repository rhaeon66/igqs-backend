from django.db import migrations, models


def seed_highlights(apps, schema_editor):
    HomeStat = apps.get_model("content", "HomeStat")
    if HomeStat.objects.exists():
        return
    HomeStat.objects.bulk_create(
        [
            HomeStat(
                value="600+",
                label_en="Total Students",
                label_bn="মোট শিক্ষার্থী",
                icon="users",
                order=1,
            ),
            HomeStat(
                value="40+",
                label_en="Expert Teachers",
                label_bn="অভিজ্ঞ শিক্ষক",
                icon="graduation-cap",
                order=2,
            ),
            HomeStat(
                value="270+",
                label_en="Students Of Merit",
                label_bn="কৃতী শিক্ষার্থী",
                icon="award",
                order=3,
            ),
            HomeStat(
                value="5+",
                label_en="Years Of Experience",
                label_bn="বছরের অভিজ্ঞতা",
                icon="sparkles",
                order=4,
            ),
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0004_heroslide"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeStat",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("value", models.CharField(max_length=40)),
                ("label_en", models.CharField(max_length=80)),
                ("label_bn", models.CharField(max_length=80)),
                (
                    "icon",
                    models.CharField(
                        choices=[
                            ("users", "Students"),
                            ("graduation-cap", "Teachers"),
                            ("award", "Award"),
                            ("sparkles", "Experience"),
                        ],
                        default="users",
                        max_length=40,
                    ),
                ),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.RunPython(seed_highlights, migrations.RunPython.noop),
    ]
