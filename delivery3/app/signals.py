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
    """
    Prevent duplicate emails only for new user registrations
    """
    if instance._state.adding:  # Only check on new user creation
        if instance.email and User.objects.filter(email=instance.email).exists():
            raise ValidationError('An account with this email already exists.')

@receiver(user_signed_up)
def handle_user_signup(sender, request, user, **kwargs):
    """Handle new user signup via Google OAuth"""
    try:
        # Get the social account data
        social_account = SocialAccount.objects.get(user=user, provider='google')
        extra_data = social_account.extra_data
        
        # Generate unique username if needed
        base_username = user.email.split('@')[0]
        username = base_username
        counter = 1
        
        while User.objects.filter(username=username).exclude(id=user.id).exists():
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
        # Log the error and optionally delete the user if profile creation fails
        print(f"Error creating user profile: {str(e)}")
        if UserProfile.objects.filter(user=user).exists():
            UserProfile.objects.filter(user=user).delete()
        user.delete()
        raise