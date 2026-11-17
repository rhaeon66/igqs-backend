from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0010_chairman_title_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="homecontent",
            name="principal_title_en",
            field=models.CharField(max_length=400),
        ),
        migrations.AlterField(
            model_name="homecontent",
            name="principal_title_bn",
            field=models.CharField(max_length=400),
        ),
        migrations.AlterField(
            model_name="leader",
            name="role_en",
            field=models.CharField(max_length=400),
        ),
        migrations.AlterField(
            model_name="leader",
            name="role_bn",
            field=models.CharField(max_length=400),
        ),
    ]
