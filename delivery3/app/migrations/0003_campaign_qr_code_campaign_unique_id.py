# Generated by Django 5.1.2 on 2024-11-04 19:21

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_remove_campaign_end_date_remove_campaign_start_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='campaign',
            name='qr_code',
            field=models.ImageField(blank=True, upload_to='qr_codes/'),
        ),
        migrations.AddField(
            model_name='campaign',
            name='unique_id',
            field=models.UUIDField(default=uuid.uuid4, editable=False),
        ),
    ]
