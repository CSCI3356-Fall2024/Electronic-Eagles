from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError


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
    start_time = models.DateTimeField(auto_now=False, auto_now_add=False) #ADDITION TO OUR CONTRACT
    end_time = models.DateTimeField(auto_now=False, auto_now_add=False)
    description = models.TextField()
    points = models.IntegerField() #Do we set a range on the points?

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.start_time > self.end_time:
            raise ValidationError("Start date cannot be after end date.")
        #if (self.start_date == self.end_date) and (self.start_time >= self.end_time):
            #raise ValidationError("For the same start and end date, start time must be before end time.")
