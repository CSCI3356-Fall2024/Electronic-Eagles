from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from allauth.socialaccount.models import SocialAccount
from .models import UserProfile
from .forms import UserProfileForm
from .models import UserProfile, NewsItem, CommunityPost
from app import forms

@login_required
def landing_page(request):
    if not request.user.userprofile.is_profile_complete():
        return redirect('profile_setup')
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if profile.is_complete():  # Check if the profile is complete
            return render(request, 'base.html')  # Go to landing page (base.html)
        else:
            return redirect('profile_setup')  # Redirect to profile setup
    else:
        return render(request, 'base.html')

@login_required
def profile_setup(request):
    # Check if the profile is already complete
    if request.user.userprofile.is_profile_complete():
        return redirect('landing_page')

    if request.method == 'POST':
        form = forms.CustomSignupForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            return redirect('landing_page')
    else:
        form = forms.CustomSignupForm(instance=request.user.userprofile)
    return render(request, 'profilesetup.html', {'form': form})

@login_required
def profile_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    role = 'Admin' if profile.admin else 'User'
    return render(request, 'profile.html', {'user_profile': profile, 'role': role})

def logout_view(request):
    logout(request)
    return redirect('landing_page')