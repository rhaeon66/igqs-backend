from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0005_homestat"),
    ]

    operations = [
        migrations.AddField(
            model_name="whychooseitem",
            name="image",
            field=models.ImageField(blank=True, upload_to="why/"),
        ),
        migrations.AddField(
            model_name="whychooseitem",
            name="image_url",
            field=models.URLField(blank=True),
        ),
    ]
