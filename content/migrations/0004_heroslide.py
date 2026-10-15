from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0003_admission_classes"),
    ]

    operations = [
        migrations.CreateModel(
            name="HeroSlide",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="home/slides/")),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["order", "id"]},
        ),
    ]
