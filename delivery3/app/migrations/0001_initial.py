# Generated by Django 4.2.4 on 2024-11-04 04:59

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Campaign",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("start_date", models.DateField()),
                ("start_time", models.DateTimeField()),
                ("end_date", models.DateField()),
                ("end_time", models.DateTimeField()),
                ("description", models.TextField()),
                ("points", models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("username", models.CharField(max_length=100)),
                ("name", models.CharField(max_length=100)),
                ("school", models.CharField(max_length=100)),
                ("graduation_year", models.IntegerField(default=0)),
                ("major1", models.CharField(max_length=100)),
                ("major2", models.CharField(blank=True, max_length=100, null=True)),
                (
                    "profile_picture",
                    models.ImageField(blank=True, null=True, upload_to="profile_pics/"),
                ),
                ("admin", models.BooleanField(default=False)),
                ("is_complete", models.BooleanField(default=False)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
