from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0008_home_sections"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeSection",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title_en", models.CharField(max_length=200)),
                ("title_bn", models.CharField(blank=True, max_length=200)),
                ("description_en", models.TextField()),
                ("description_bn", models.TextField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={
                "ordering": ["order", "id"],
            },
        ),
    ]
