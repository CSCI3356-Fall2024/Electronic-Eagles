from django import forms
from allauth.account.forms import SignupForm
from .models import UserProfile

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['username', 'school', 'graduation_year', 'major1', 'major2', 'profile_picture']
        widgets = {
            'graduation_year': forms.NumberInput(attrs={'min': 2020, 'max': 2030}),
        }
        
class CustomSignupForm(SignupForm):
    username = forms.CharField(max_length=30, label='Username', required=True)
    school = forms.CharField(max_length=100, label='School', required=True)
    graduation_year = forms.IntegerField(
        label='Graduation Year',
        required=True,
        widget=forms.NumberInput(attrs={'min': 2020, 'max': 2030})
    )
    major1 = forms.CharField(max_length=100, label='Primary Major', required=True)
    major2 = forms.CharField(max_length=100, label='Second Major (Optional)', required=False)
    profile_picture = forms.ImageField(label='Profile Picture', required=False)

    def save(self, request):
        # Save the user by calling the parent class's save method
        user = super(CustomSignupForm, self).save(request)

        # Create or update the user profile
        user_profile, created = UserProfile.objects.get_or_create(user=user)
        user_profile.school = self.cleaned_data['school']
        user_profile.graduation_year = self.cleaned_data['graduation_year']
        user_profile.major1 = self.cleaned_data['major1']
        user_profile.major2 = self.cleaned_data.get('major2', '')
        user_profile.profile_picture = self.cleaned_data.get('profile_picture')
        user_profile.save()

        return user
