from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import logout
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from datetime import timedelta
from .forms import UserProfileForm, CampaignForm, NewsForm
from .models import UserProfile, Campaign, ActivityLog, News
from django.db import transaction
from app import forms
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.utils.timezone import now
from allauth.account.models import EmailAddress
from .forms import RewardForm
from .models import Reward
from django.db.models import Q


@login_required
@require_http_methods(["POST"])
def validate_campaign(request, campaign_id):
    try:
        campaign = Campaign.objects.get(unique_id=campaign_id)
        
        # Check if campaign is active (handles both permanent and regular campaigns)
        if not campaign.is_active:
            return JsonResponse({
                'success': False,
                'message': 'This campaign is not currently active.'
            })

        # Check if user has already redeemed
        if request.user in campaign.redeemed_users.all():
            return JsonResponse({
                'success': False,
                'message': 'You have already redeemed this campaign.'
            })
        
        # Award points and log activity
        with transaction.atomic():
            user_profile = request.user.userprofile
            user_profile.points += campaign.points
            user_profile.save()

            # Log the activity
            try:
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type="EARNED",
                    description=f"Earned {campaign.points} points from {campaign.name} {'(Permanent Campaign)' if campaign.permanent else ''}.",
                    points=f"+{campaign.points}",
                    timestamp=timezone.now(),
                )
            except Exception as e:
                print(f"Failed to log activity: {e}", flush=True)

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
    now = timezone.now()
    featured_campaigns = Campaign.objects.none()
    news = News.objects.none()
    top_users = []  # Default value if no users exist

    if request.user.is_authenticated:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        featured_campaigns = Campaign.objects.filter(
            newsfeed=True, 
            start_time__lte=now,
            end_time__gt=now
        ).order_by('-start_time')
        news = News.objects.filter(
            start_time__lte=now,
            end_time__gt=now
        ).order_by('-start_time')

        if not profile.is_complete:
            return redirect('profile_setup')

        # Handle the logic for top users
        if UserProfile.objects.exists():  # Check if any users exist
            # Check if users have points
            if UserProfile.objects.filter(points__gt=0).exists():
                # Rank users by descending points if points exist
                top_users = UserProfile.objects.order_by('-points')[:5]
            else:
                # Otherwise, include all users
                top_users = UserProfile.objects.all()[:5]

    return render(request, 'landing_page.html', {
        'featured_campaigns': featured_campaigns,
        'news': news,
        'top_users': top_users,
    })


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
            try:
                with transaction.atomic():
                    campaign = form.save(commit=False)
                    if campaign.permanent:
                        # Set far future dates for permanent campaigns
                        campaign.start_time = timezone.now()
                        campaign.end_time = timezone.now() + timezone.timedelta(days=36500)  # 100 years
                    campaign.save()
                messages.success(request, "Campaign created successfully!")
                return redirect('active_campaigns')
            except Exception as e:
                messages.error(request, str(e))
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = forms.CampaignForm()
    return render(request, 'campaign_create.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def active_campaigns_view(request):
    now = timezone.now()
    permanent_campaigns = Campaign.objects.filter(permanent=True)

    active_campaigns = Campaign.objects.filter(
        permanent=False,
        start_time__lte=now,
        end_time__gt=now
    ).prefetch_related('redeemed_users')
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
    user = request.user
    rewards = Reward.objects.all()
    if request.user.is_superuser:
        form = RewardForm(request.POST or None, request.FILES or None)
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

        elif 'reward_id' in request.POST:
            reward_id = request.POST.get('reward_id')
            reward = get_object_or_404(Reward, id=reward_id)
            if user_profile.points >= reward.points_required:
                user_profile.points -= reward.points_required
                user_profile.save()
                messages.success(request, f"You have successfully redeemed {reward.name} for {reward.points_required} points.")
                
                ActivityLog.objects.create(
                    user=request.user,
                    activity_type='REDEEMED',
                    points=-reward.points_required,
                    description=f"Redeemed {reward.points_required} points for reward: {reward.name}"
                )

                rewardResponse = f'You have succesfully redeemed {reward.name} for {reward.points_required} points! Check email for more details.'
                try:
                    user = request.user
                    email_address = EmailAddress.objects.filter(user=user, primary=True).first()
                    send_mail(
                        'Redeemed Reward!',
                        f'You have successfully redeemed {reward.name} for {reward.points_required} points! '
                        'Thank you for keeping the environment clean. Your efforts are not going unnoticed. '
                        'The dev team here at Eco Edu hopes you enjoy your reward.',
                        'blest@bc.edu',
                        [email_address.email],
                        fail_silently=False,
                    )
                    messages.success(request, "Points successfully redeemed and email sent!")

                except Exception as e:
                    messages.error(request, f"Points redeemed but failed to send email: {str(e)}")

            else:
                messages.error(request, f"Not enough points to redeem {reward.name}. You need {reward.points_required - user_profile.points} more points.")

            return redirect ('rewards')

        elif 'delete_reward_id' in request.POST:
            reward_id = request.POST['delete_reward_id']
            reward = get_object_or_404(Reward, id=reward_id)
            reward.delete()
            messages.success(request, "Reward successfully deleted.")
            return redirect('rewards')

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

        elif request.user.is_superuser and 'name' in request.POST:
            form = RewardForm(request.POST, request.FILES)
            if form.is_valid():
                form.save()
                messages.success(request, "Reward added successfully!")
                return redirect ('rewards')
            else:
                messages.error(request, "Failed to add reward. Please check the form and try again.")

        else:
            messages.error(request, "No item name or point total.")

    context = {'points': user_profile.points, 'rewards': Reward.objects.all(), 'rewardResponse': rewardResponse, 'form' : form if request.user.is_superuser else None}
    return render(request, 'rewards.html', context)


@login_required
def activity_view(request):
    user = request.user
    user_profile = user.userprofile
    user_points = user_profile.points
    # Get al activity logs related to the user
    activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')
    
    return render(request, 'activity.html', {'activities': activities, 'user_points': user_points})

@login_required
def campaign_activity_view(request):
    user = request.user
    user_profile = user.userprofile
    user_points = user_profile.points
    # Get al activity logs related to the user
    activities = ActivityLog.objects.filter(user=user).order_by('-timestamp')
    
    return render(request, 'activity.html', {'activities': activities, 'user_points': user_points})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def news_create_view(request):
    if request.method == 'POST':
        form = forms.NewsForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    news = form.save(commit=False)
                    news.save()
                messages.success(request, "News created successfully!")
                return redirect('active_news')
            except Exception as e:
                # Log the exception (optional)
                print(f"Error occurred while creating news: {e}")
                messages.error(request, "An error occurred while saving the news. Please try again.")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = forms.NewsForm()
    return render(request, 'news_create.html', {'form': form})

@login_required
@user_passes_test(lambda u: u.is_superuser)
def active_news_view(request):
    now = timezone.now()

    active_news = News.objects.filter(
        start_time__lte=now,
        end_time__gt=now
    )
    inactive_news = News.objects.exclude(
        pk__in=active_news.values_list('pk', flat=True)
    )

    return render(request, 'active_news.html', {
        'active_news': active_news,
        'inactive_news': inactive_news,
        'now': now
    })

@login_required
@user_passes_test(lambda u: u.is_superuser)
def edit_news_view(request, pk):
    news = get_object_or_404(News, pk=pk)
    if request.method == 'POST':
        if 'delete_news' in request.POST:
            news.delete()
            messages.success(request, "News deleted successfully!")
            return redirect('active_news')
        form = NewsForm(request.POST, request.FILES, instance=news)
        if form.is_valid():
            form.save()
            messages.success(request, "News updated successfully!")
            return redirect('active_news')
        else:
            print(form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = NewsForm(instance=news)
    return render(request, 'edit_news.html', {'form': form, 'news': news})
    
    