from django import forms
from django.core.exceptions import ValidationError
from allauth.account.forms import SignupForm
from .models import UserProfile, Campaign, Reward, News
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
        fields = ['name', 'start_time', 'end_time', 'description', 'points', 'cover_photo', 'permanent', 'newsfeed']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
            'permanent': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'id': 'permanent-checkbox'
            })
        }

    def clean(self):
        cleaned_data = super().clean()
        permanent = cleaned_data.get('permanent')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if not permanent and (not start_time or not end_time):
            raise ValidationError('Start and end times are required for non-permanent campaigns.')

        return cleaned_data


class RewardForm(forms.ModelForm):
    class Meta:
        model = Reward
        fields = ['name', 'description', 'points_required', 'image']

class NewsForm(forms.ModelForm):
    class Meta:
        model = News
        fields = ['title', 'author', 'description', 'image', 'start_time', 'end_time']
        widgets = {
            'start_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'required': True #The error changed once I added this
            }),
            'end_time': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control',
                'required': True
            })
        }
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')

        if not start_time or not end_time:
            raise forms.ValidationError("Start time and end time are required.")
        
        if start_time > end_time:
            raise forms.ValidationError("Start time cannot be after end time.")
        
        return cleaned_data

