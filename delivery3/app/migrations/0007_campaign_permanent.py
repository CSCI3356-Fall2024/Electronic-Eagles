# Generated by Django 5.1.3 on 2024-11-22 02:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0006_campaign_cover_photo'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='permanent',
            field=models.BooleanField(default=False),
        ),
    ]