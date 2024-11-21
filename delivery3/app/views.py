from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from .models import UserProfile
from .forms import UserProfileForm, CampaignForm
from .models import UserProfile, Campaign
from django.db import transaction
from app import forms
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from allauth.account.models import EmailAddress

@require_http_methods(["POST"])
def validate_campaign(request, campaign_id):
    try:
        # Get the campaign
        campaign = Campaign.objects.get(unique_id=campaign_id)
        
        # Check if campaign is active
        now = timezone.now()
        if campaign.start_time > now:
            return JsonResponse({
                'success': False,
                'message': 'This campaign has not started yet.'
            })
        
        if campaign.end_time < now:
            return JsonResponse({
                'success': False,
                'message': 'This campaign has ended.'
            })
        
        # Get user profile and add points
        user_profile = request.user.userprofile
        user_profile.points += campaign.points
        user_profile.save()
        
        return JsonResponse({
            'success': True,
            'points': campaign.points,
            'total_points': user_profile.points
        })
        
    except Campaign.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid QR code.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing the QR code.'
        })


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
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save the profile
                    profile = form.save(commit=False)
                    profile.user = request.user
                    profile.is_complete = True
                    profile.save()
                    
                    # Update the User model username to match
                    request.user.username = profile.username
                    request.user.save()
                    
                return redirect('profile')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        form = UserProfileForm(instance=profile)
    
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
    now = timezone.now()
    return render(request, 'actions.html', {'campaigns': campaigns, 'now': now})


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

@login_required
def rewards_view(request):
    user_profile = request.user.userprofile
    if request.method == 'POST':
        if 'campaign_id' in request.POST:
            campaign_id = request.POST.get('campaign_id')
            if campaign_id:
                campaign = get_object_or_404(Campaign, pk=campaign_id)
                if request.user not in campaign.redeemed_users.all():
                    user_profile.points += campaign.points
                    user_profile.save()
                    campaign.redeemed_users.add(request.user)
                    messages.success(request, "Points redeemed successfully!")
                else:
                    messages.error(request, "You have already redeemed this campaign.")
                return redirect('actions')
        
        elif 'points_to_subtract' and 'item_name' in request.POST:
            points_to_subtract = int(request.POST.get('points_to_subtract', 0))
            item_name = request.POST.get('item_name')
            if user_profile.points >= points_to_subtract:
                user_profile.points -= points_to_subtract
                user_profile.save()
                messages.success(request, "Points successfully subtracted!")

                try:
                   user = request.user
                   email_address = EmailAddress.objects.filter(user=user, primary=True).first()
                   send_mail(
                       'Redeemed event',
                       f'You have successfully redeemed {item_name} for {points_to_subtract} points! Thank you for keeping the environment clean. Your efforts are not going unnoticed. The dev team here at Eco Edu hopes you enjoy your reward.',
                       'blest@bc.edu',
                       [email_address.email],
                       fail_silently=False,
                   )
                   messages.success(request, "Email sent successfully!")

                except Exception as e:
                   messages.error(request, f"Failed to send email: {str(e)}")

                return redirect('rewards')
            else:
                messages.error(request, "Not enough points")
        

    return render(request, 'rewards.html', {'points': user_profile.points})
