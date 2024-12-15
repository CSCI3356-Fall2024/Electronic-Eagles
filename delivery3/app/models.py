from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.core.exceptions import ValidationError
import qrcode
from io import BytesIO
from django.core.files import File
import uuid
from django.utils import timezone

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
    is_complete = models.BooleanField(default=False)
    points = models.IntegerField(default=0)

    def __str__(self):
        return self.user.username

class Campaign(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    description = models.TextField()
    points = models.IntegerField()
    cover_photo = models.ImageField(upload_to='campaign_pics/', blank=True, null=True)
    permanent = models.BooleanField(default=False)
    # New fields for QR code
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    unique_id = models.UUIDField(default=uuid.uuid4, editable=False)
    redeemed_users = models.ManyToManyField(User, blank=True, related_name='redeemed_campaigns')
    newsfeed = models.BooleanField(default=False)

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
        return self.end_time < timezone.now()

    @property
    def is_active(self):
        if self.permanent:
            return True
        now = timezone.now()
        return self.start_time <= now <= self.end_time

    def can_redeem(self, user):
        """Check if a user can redeem this campaign"""
        if not self.permanent:
            now = timezone.now()
            if not (self.start_time <= now <= self.end_time):
                return False
        return user not in self.redeemed_users.all()
    
class ActivityLog(models.Model):
    ACTIVITY_CHOICES = [
        ('EARNED', 'Earned Points'),
        ('REDEEMED', 'Redeemed Points')
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity_type = models.CharField(max_length=10, choices=ACTIVITY_CHOICES, default="Default Action")
    points = models.CharField(default="0", max_length=10)
    description = models.TextField(default="Default Action")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.points} points"
    
class Reward(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    points_required = models.PositiveIntegerField()
    image = models.ImageField(upload_to='rewards/', blank=True, null=True)

    def __str__(self):
        return f"{self.name} (Points needed: {self.points_required})" 

class News(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='news/', blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        start_time = self.start_time
        end_time = self.end_time
        if start_time and end_time:
            if self.start_time > self.end_time:
                raise ValidationError("Start date cannot be after end date.")
        else:
            raise ValidationError("Start time and end time are required.")


    #def save(self, *args, **kwargs):
    #    self.full_clean()  # Ensures clean() runs before saving
    #    super().save(*args, **kwargs)



