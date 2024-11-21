from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from allauth.account.signals import user_signed_up
from allauth.socialaccount.models import SocialAccount
from django.core.exceptions import ValidationError
from django.db import transaction
from .models import UserProfile

@receiver(pre_save, sender=User)
def prevent_duplicate_email(sender, instance, **kwargs):
    """Prevent users from having duplicate emails"""
    if instance.email:
        existing_user = User.objects.filter(email=instance.email).exclude(id=instance.id).first()
        if existing_user:
            raise ValidationError('An account with this email already exists.')

@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    """Handle new user signup via Google OAuth"""
    try:
        # Get the social account data
        social_account = SocialAccount.objects.get(user=user, provider='google')
        extra_data = social_account.extra_data
        
        # Check for existing email
        email = user.email
        if User.objects.filter(email=email).exclude(id=user.id).exists():
            user.delete()
            raise ValidationError('An account with this email already exists.')
        
        # Generate unique username if needed
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user.username = username
        user.save()
        
        # Create UserProfile
        UserProfile.objects.create(
            user=user,
            username=username,
            name=extra_data.get('name', ''),
            school='',
            graduation_year=0000,
            major1='',
            is_complete=False
        )
        
    except Exception as e:
        # Clean up if profile creation fails
        if UserProfile.objects.filter(user=user).exists():
            UserProfile.objects.filter(user=user).delete()
        user.delete()
        raise