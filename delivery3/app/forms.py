from django import forms
from allauth.account.forms import SignupForm
from .models import UserProfile, Campaign

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['username', 'name', 'school', 'graduation_year', 'major1', 'major2', 'profile_picture']
        widgets = {
            'graduation_year': forms.NumberInput(attrs={'min': 2020, 'max': 2030}),
        }
        
class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'start_time', 'end_time', 'description', 'points']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'end_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
        
