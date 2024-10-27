from django.contrib import admin

from .models import UserProfile, Campaign

# Register your models here.
admin.site.register(UserProfile)
admin.site.register(Campaign)