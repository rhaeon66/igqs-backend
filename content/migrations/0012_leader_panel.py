from django.db import migrations, models


def organize_people(apps, schema_editor):
    Leader = apps.get_model("content", "Leader")
    HomeContent = apps.get_model("content", "HomeContent")

    def panel_for(role_en, role_bn):
        text = f"{role_en}\n{role_bn}".lower()
        is_advisor = "advisor" in text or "উপদেষ্টা" in text
        if not is_advisor and ("chairman" in text or "চেয়ারম্যান" in text):
            return "chairman"
        if not is_advisor and (
            "principal" in text or "প্রিন্সিপাল" in text or "অধ্যক্ষ" in text
        ):
            return "principal"
        if not is_advisor and (
            "teacher" in text or "শিক্ষক" in text or "উস্তাদ" in text or "উস্তাজা" in text
        ):
            return "teacher"
        if not is_advisor and ("director" in text or "পরিচালক" in text):
            return "director"
        if is_advisor:
            return "advisor"
        return "director"

    for person in Leader.objects.all():
        person.panel = panel_for(person.role_en or "", person.role_bn or "")
        person.save(update_fields=["panel"])

    chair = Leader.objects.filter(panel="chairman").order_by("order", "id").first()
    home = HomeContent.objects.order_by("id").first()
    if not chair or not home:
        return
    changed = []
    if not (home.chairman_name_en or "").strip():
        home.chairman_name_en = chair.name_en
        home.chairman_name_bn = chair.name_bn
        changed += ["chairman_name_en", "chairman_name_bn"]
    if not (home.chairman_title_en or "").strip():
        home.chairman_title_en = chair.role_en
        home.chairman_title_bn = chair.role_bn
        changed += ["chairman_title_en", "chairman_title_bn"]
    if changed:
        home.save(update_fields=changed)


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0011_designation_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="leader",
            name="panel",
            field=models.CharField(
                choices=[
                    ("chairman", "Chairman"),
                    ("principal", "Principal"),
                    ("director", "Director"),
                    ("teacher", "Teacher"),
                    ("advisor", "Advisor"),
                ],
                default="advisor",
                max_length=20,
            ),
        ),
        migrations.RunPython(organize_people, migrations.RunPython.noop),
    ]
