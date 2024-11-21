from django import forms
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm
from .models import UserProfile, Campaign
from django.contrib.auth.models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['username', 'name', 'school', 'graduation_year', 'major1', 'major2', 'profile_picture']
        widgets = {
            'graduation_year': forms.NumberInput(attrs={'min': 2020, 'max': 2030}),
        }
        
        def clean_username(self):
            username = self.cleaned_data.get('username')
            # Exclude current user from the check
            if self.instance and self.instance.pk:
                if User.objects.filter(username=username).exclude(id=self.instance.user.id).exists():
                    raise ValidationError('This username is already taken.')
            else:
                if User.objects.filter(username=username).exists():
                    raise ValidationError('This username is already taken.')
            return username
            
class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'start_time', 'end_time', 'description', 'points']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        
