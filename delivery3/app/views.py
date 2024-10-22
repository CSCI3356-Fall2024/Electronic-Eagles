from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from allauth.socialaccount.models import SocialAccount
from .models import UserProfile
from .forms import UserProfileForm
from .models import UserProfile
from app import forms

def landing_page(request):
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not profile.is_complete:
            return redirect('profile_setup')
        else:
            return redirect('profile')
    return render(request, 'base.html')


@login_required
def profile_view(request):
    profile = get_object_or_404(UserProfile, user=request.user)
    return render(request, 'profile.html', {'profile': profile})

def first(request):
    complete = request.user.is_complete

    if complete == True:
        return redirect('landing_page')
    else:
        return redirect('profile_setup')

@login_required
def profile_setup(request):
    profile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = forms.UserProfileForm(request.POST, instance=request.user.userprofile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.user = request.user
            profile.is_complete = True
            profile.save()
            return redirect('profile')
    else:
        form = forms.UserProfileForm(instance=request.user.userprofile)
    return render(request, 'profile_setup.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('landing_page')