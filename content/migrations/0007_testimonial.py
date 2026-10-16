from datetime import datetime, timezone

from django.db import migrations, models


def seed_testimonials(apps, schema_editor):
    Testimonial = apps.get_model("content", "Testimonial")
    if Testimonial.objects.exists():
        return
    Testimonial.objects.bulk_create(
        [
            Testimonial(
                name_en="Amina Karim",
                name_bn="আমিনা করিম",
                role="guardian",
                quote_en="My child comes home reciting with care. The teachers correct gently and never rush a student.",
                quote_bn="আমার সন্তান যত্নসহ তিলাওয়াত করে বাড়ি ফেরে। শিক্ষকরা ধীরে ধীরে শুধরে দেন, কাউকে তাড়াহুড়ো করান না।",
                spoken_on=datetime(2026, 8, 12, tzinfo=timezone.utc),
                rating=5,
                order=1,
            ),
            Testimonial(
                name_en="Yusuf Hasan",
                name_bn="ইউসুফ হাসান",
                role="student",
                quote_en="I like reading the Qur'an here. When I miss a line, my teacher stays until I can say it properly.",
                quote_bn="এখানে কুরআন পড়তে আমার ভালো লাগে। কোনো লাইন বাদ পড়লে শিক্ষক ঠিকমতো বলতে না পারা পর্যন্ত সাথে থাকেন।",
                spoken_on=datetime(2026, 2, 3, tzinfo=timezone.utc),
                rating=5,
                order=2,
            ),
            Testimonial(
                name_en="Fatima Noor",
                name_bn="ফাতিমা নূর",
                role="guardian",
                quote_en="Salah, character, and school subjects sit together here. That is the balance we wanted for our daughter.",
                quote_bn="এখানে সালাত, চরিত্র ও স্কুলের পড়া একসাথে চলে। মেয়ের জন্য আমরা এই ভারসাম্যই চেয়েছিলাম।",
                spoken_on=datetime(2026, 1, 18, tzinfo=timezone.utc),
                rating=5,
                order=3,
            ),
        ]
    )


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0006_whychooseitem_image"),
    ]

    operations = [
        migrations.CreateModel(
            name="Testimonial",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name_en", models.CharField(max_length=120)),
                ("name_bn", models.CharField(max_length=120)),
                (
                    "role",
                    models.CharField(
                        choices=[("guardian", "Guardian"), ("student", "Student")],
                        default="guardian",
                        max_length=20,
                    ),
                ),
                ("quote_en", models.TextField()),
                ("quote_bn", models.TextField()),
                ("spoken_on", models.DateTimeField(blank=True, null=True)),
                ("rating", models.PositiveSmallIntegerField(default=5)),
                ("facebook_url", models.URLField(blank=True)),
                ("image", models.ImageField(blank=True, upload_to="testimonials/")),
                ("image_url", models.URLField(blank=True)),
                ("order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["order", "id"]},
        ),
        migrations.RunPython(seed_testimonials, migrations.RunPython.noop),
    ]
