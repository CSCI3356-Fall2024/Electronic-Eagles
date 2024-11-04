from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from allauth.socialaccount.models import SocialAccount
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.contrib.auth.models import User
from .models import UserProfile
from .forms import UserProfileForm, CampaignForm
from .models import UserProfile, Campaign
from app import forms
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404


def landing_page(request):
    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        if not profile.is_complete:
            return redirect('profile_setup')
    return render(request, 'landing_page.html')


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

@login_required
def campaign_create_view(request):
    if request.method == 'POST':
        form = forms.CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            messages.success(request, "Campaign created successfully!")
            campaign.save()
            return redirect('active_campaigns')
        else:
            print("Form errors:", form.errors)  
    else:
        form = forms.CampaignForm()

    return render(request, 'campaign_create.html', {'form': form})

@login_required
def active_campaigns_view(request):
    now = timezone.now()
    active_campaigns = Campaign.objects.filter(
        start_time__lte=now,
        end_time__gt=now
    )
    inactive_campaigns = Campaign.objects.exclude(
        pk__in=active_campaigns.values_list('pk', flat=True)
    )
    return render(request, 'active_campaigns.html', {
        'active_campaigns': active_campaigns,
        'inactive_campaigns': inactive_campaigns
    })



@login_required
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

@login_required
def actions_view(request):
    campaigns = Campaign.objects.all()
    return render(request, 'actions.html', {'campaigns': campaigns})


@login_required
@user_passes_test(lambda u: u.is_superuser)  # Ensure only superusers can access this
def change_admin_status(request):
    profile = get_object_or_404(UserProfile, user=request.user)

    if request.method == "POST":
        username = request.POST.get("username")
        action = request.POST.get("action")

        if not username:
            messages.error(request, "Please enter a valid username.")
            return render(request, 'profile.html', {'profile': profile})

        try:
            user = User.objects.get(username=username)
            user_profile = UserProfile.objects.get(user__username=username)
        except UserProfile.DoesNotExist:
            messages.error(request, f"No user found with username '{username}'.")
            return render(request, 'profile.html', {'profile': profile})  
        
        if action == "make_admin":
            user_profile.admin = True
            user.is_superuser = True
            messages.success(request, f"{username} has been given admin privileges.")
        elif action == "remove_admin":
            user_profile.admin = False
            user.is_superuser = False
            messages.success(request, f"{username}'s admin privileges have been removed.")

        user.save()
        user_profile.save()

        return render(request, 'profile.html', {'profile': profile})
    
    return render(request, 'profile.html', {'profile': profile})

@user_passes_test(lambda u: u.is_staff)
def view_campaign_details(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return render(request, 'campaign_details.html', {
        'campaign': campaign
    })

