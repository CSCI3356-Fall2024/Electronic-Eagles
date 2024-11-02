from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.utils import timezone
from .models import UserProfile
from .forms import UserProfileForm, CampaignForm
from .models import UserProfile, Campaign
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
        form = forms.UserProfileForm(request.POST, request.FILES, instance=request.user.userprofile)
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

#LEFT OUT LOGIN REQUIREMENT FOR DEBUGGING
def campaign_create_view(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Campaign created successfully!")
                return redirect('active_campaigns')  
            except ValidationError as e:
                form.add_error(None, e)
        else:
            messages.error(request, "There was an error with your submission.")
    else:
        form = CampaignForm()

    return render(request, 'campaign_create.html', {'form': form})

# List all active campaigns
def active_campaigns_view(request):
    today = timezone.now().date()
    campaigns = Campaign.objects.filter(start_date__lte=today, end_date__gte=today)
    return render(request, 'active_campaigns.html', {'campaigns': campaigns})

# Edit a specific campaign
def edit_campaign_view(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        form = CampaignForm(request.POST, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "Campaign updated successfully!")
            return redirect('active_campaigns')  
    else:
        form = CampaignForm(instance=campaign)
    return render(request, 'edit_campaign.html', {'form': form, 'campaign': campaign})


    