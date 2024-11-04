from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import qrcode
from io import BytesIO
from django.core.files import File
import uuid

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    username = models.CharField(max_length=100)
    name = models.CharField(max_length=100)
    school = models.CharField(max_length=100)
    graduation_year = models.IntegerField(default=0000)
    major1 = models.CharField(max_length=100)
    major2 = models.CharField(max_length=100, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    admin = models.BooleanField(default=False)
    is_complete = models.BooleanField(default = False)

    def __str__(self):
        return self.user.username
    
class Campaign(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField(auto_now=False, auto_now_add=False)
    end_time = models.DateTimeField(auto_now=False, auto_now_add=False)
    description = models.TextField()
    points = models.IntegerField()
    # New fields for QR code
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_time > self.end_time:
            raise ValidationError("Start date cannot be after end date.")

    def save(self, *args, **kwargs):
        # Generate QR code if it doesn't exist
        if not self.qr_code:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(f'campaign:{self.unique_id}')
            qr.make(fit=True)
            
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code image
            buffer = BytesIO()
            qr_image.save(buffer, format='PNG')
            filename = f'qr_code-{self.unique_id}.png'
            self.qr_code.save(filename, File(buffer), save=False)
            
        super().save(*args, **kwargs)
    
    @property
    def is_past_campaign(self):
        from django.utils import timezone
        return self.end_time < timezone.now()