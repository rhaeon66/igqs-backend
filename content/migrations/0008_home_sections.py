from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0007_testimonial"),
    ]

    operations = [
        migrations.AddField(
            model_name="homecontent",
            name="chairman_name_en",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_name_bn",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_title_en",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_title_bn",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_message_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_message_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_photo",
            field=models.ImageField(blank=True, upload_to="home/"),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="chairman_photo_url",
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="goals_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="goals_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="beacon_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="beacon_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="dreams_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="dreams_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="child_gain_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="child_gain_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="holistic_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="holistic_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="admission_procedures_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="admission_procedures_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="tuition_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="tuition_bn",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="uniform_en",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="homecontent",
            name="uniform_bn",
            field=models.TextField(blank=True),
        ),
    ]
