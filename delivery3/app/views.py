from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from datetime import timedelta
from .models import UserProfile
from .forms import UserProfileForm, CampaignForm
from .models import UserProfile, Campaign, ActivityLog
from django.db import transaction
from app import forms
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.utils.timezone import now
from allauth.account.models import EmailAddress

@login_required
@require_http_methods(["POST"])
def validate_campaign(request, campaign_id):
    try:
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

        # Check if user has already redeemed
        if request.user in campaign.redeemed_users.all():
            return JsonResponse({
                'success': False,
                'message': 'You have already redeemed this campaign.'
            })
        
        # Get user profile and add points
        with transaction.atomic():
            user_profile = request.user.userprofile
            user_profile.points += campaign.points
            user_profile.save()

            # Safely log the activity
            try:
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type="EARNED",
                    description=f"Earned {campaign.points} points from campaign {campaign.name}.",
                    points=f"+{campaign.points}",
                    timestamp=timezone.now,
                )
                print(f"Activity logged for {request.user.username}: Earned {campaign.points} points", flush=True)
            except Exception as e:
                print(f"Failed to log activity: {e}", flush=True)

            # Add user to redeemed users
            campaign.redeemed_users.add(request.user)
        
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
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            messages.success(request, "Profile picture updated successfully!")
            return redirect('profile')
        
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
        else:
            # Remove username from errors if present
            errors = form.errors.copy()
            errors.pop('username', None)
           
            if errors:
                # If other errors exist, show them
                for field, error_list in errors.items():
                    for error in error_list:
                        messages.error(request, f"{field.capitalize()}: {error}")
            else:
                # If only username error, still try to save valid fields
                cleaned_data = {k: v for k, v in form.cleaned_data.items() if k != 'username'}
                for field, value in cleaned_data.items():
                    setattr(profile, field, value)
                profile.save()
                messages.success(request, "Profile updated successfully!")
            
            return redirect('profile')
            
    
    profile_fields = [
        {'name': 'name', 'label': 'Name', 'value': profile.name},
        {'name': 'school', 'label': 'School', 'value': profile.school},
        {'name': 'graduation_year', 'label': 'Graduation Year', 'value': profile.graduation_year},
        {'name': 'major1', 'label': 'Primary Major', 'value': profile.major1},
        {'name': 'major2', 'label': 'Second Major', 'value': profile.major2 or 'N/A'}
    ]
    
    return render(request, 'profile.html', {
        'profile': profile,
        'profile_fields': profile_fields
    })

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
                    
                messages.success(request, "Profile updated successfully!")
                return redirect('profile')
            except ValidationError as e:
                messages.error(request, str(e))
    else:
        # For GET requests, pre-fill the username field
        initial_data = {'username': request.user.username}
        form = UserProfileForm(instance=profile, initial=initial_data)
    
    return render(request, 'profile_setup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('landing_page')

@login_required
@user_passes_test(lambda u: u.is_superuser)
def campaign_create_view(request):
    if request.method == 'POST':
        form = forms.CampaignForm(request.POST, request.FILES)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.save()
            messages.success(request, "Campaign created successfully!")
            return redirect('active_campaigns')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = forms.CampaignForm()

    return render(request, 'campaign_create.html', {'form': form})
@login_required
def active_campaigns_view(request):
    now = timezone.now()
    permanent_campaigns = Campaign.objects.filter(permanent=True)

    active_campaigns = Campaign.objects.filter(
        permanent=False,
        start_time__lte=now,
        end_time__gt=now
    )
    inactive_campaigns = Campaign.objects.filter(permanent=False).exclude(
        pk__in=active_campaigns.values_list('pk', flat=True)
    )

    return render(request, 'active_campaigns.html', {
        'active_campaigns': active_campaigns,
        'inactive_campaigns': inactive_campaigns,
        'permanent_campaigns': permanent_campaigns,
        'now': now
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_campaign_view(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    if request.method == 'POST':
        if 'delete_campaign' in request.POST:
            campaign.delete()
            messages.success(request, "Campaign deleted successfully!")
            return redirect('active_campaigns')
        form = CampaignForm(request.POST, request.FILES, instance=campaign)
        if form.is_valid():
            form.save()
            messages.success(request, "Campaign updated successfully!")
            return redirect('active_campaigns')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CampaignForm(instance=campaign)
    return render(request, 'edit_campaign.html', {'form': form, 'campaign': campaign})

@login_required
def actions_view(request):
    now = timezone.now()
    # Get all campaigns ordered by start time
    campaigns = Campaign.objects.filter(permanent=False).order_by('-start_time')
    permanent_campaigns = Campaign.objects.filter(permanent=True)
    user_profile = UserProfile.objects.get(user=request.user)
    points = user_profile.points

    campaign_context = []
    upcoming_campaigns = []

    for campaign in campaigns:
        # Check if the campaign is active
        if campaign.start_time <= now <= campaign.end_time:
            campaign_context.append({
                'campaign': campaign,
                'is_active': True,
                'can_redeem': campaign.can_redeem(request.user),
            })
        elif campaign.start_time > now:  # Add to upcoming campaigns
            upcoming_campaigns.append(campaign)

    return render(request, 'actions.html', {
        'permanent_campaigns': permanent_campaigns,
        'campaign_context': campaign_context,
        'upcoming_campaigns': upcoming_campaigns,
        'now': now,
        'points': points,
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
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
        except (User.DoesNotExist, UserProfile.DoesNotExist):
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

@login_required
@user_passes_test(lambda u: u.is_staff)
def view_campaign_details(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    return render(request, 'campaign_details.html', {
        'campaign': campaign
    })

@login_required
def rewards_view(request):
    user_profile = request.user.userprofile
    rewardResponse = ""

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
                    print(f"Logging activity for user {request.user.username}")

                    ActivityLog.objects.create(
                        user=request.user,
                        activity_type='EARNED',
                        points=campaign.points,
                        description=f"Earned {campaign.points} points from campaign: {campaign.name}"
                    )
                else:
                    messages.error(request, "You have already redeemed this campaign.")
                return redirect('actions')

        elif 'points_to_subtract' in request.POST and 'item_name' in request.POST:
            points_to_subtract = int(request.POST.get('points_to_subtract', 0))
            item_name = request.POST.get('item_name')
            rewardResponse = f'Not enough points for {item_name} need {points_to_subtract - user_profile.points} more points!'
            if user_profile.points >= points_to_subtract:
                user_profile.points -= points_to_subtract
                user_profile.save()

                ActivityLog.objects.create(
                    user=request.user,
                    activity_type='REDEEMED',
                    points=f"-{points_to_subtract}",
                    description=f"Redeemed {points_to_subtract} points for reward: {item_name}"
                )

                rewardResponse = f'You have succesfully redeemed {item_name} for {points_to_subtract} points! Check email for more details.'
                try:
                    user = request.user
                    email_address = EmailAddress.objects.filter(user=user, primary=True).first()
                    send_mail(
                        'Redeemed Reward!',
                        f'You have successfully redeemed {item_name} for {points_to_subtract} points! '
                        'Thank you for keeping the environment clean. Your efforts are not going unnoticed. '
                        'The dev team here at Eco Edu hopes you enjoy your reward.',
                        'blest@bc.edu',
                        [email_address.email],
                        fail_silently=False,
                    )
                    messages.success(request, "Points successfully redeemed and email sent!")

                except Exception as e:
                    messages.error(request, f"Points redeemed but failed to send email: {str(e)}")

            return redirect('rewards')
        else:
            messages.error(request, "No item name or point total.")

            
    
    return render(request, 'rewards.html', {'points': user_profile.points, 'rewardResponse': rewardResponse})

@login_required
def activity_view(request):
    user = request.user
    user_profile = user.userprofile
    user_points = user_profile.points
    # Get al activity logs related to the user
    activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')
    
    return render(request, 'activity.html', {'activities': activities, 'user_points': user_points})
    