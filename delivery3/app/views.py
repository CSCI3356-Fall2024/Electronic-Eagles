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
        if not profile.is_complete():
            return redirect('profile_setup')
        
        # Fetch data for the template
        leaderboard = UserProfile.objects.order_by('-points')[:5]
        news_items = NewsItem.objects.order_by('-date')[:2]
        community_posts = CommunityPost.objects.order_by('-date')[:2]
        
        context = {
            'profile': profile,
            'leaderboard': [
                {
                    'initials': user.user.username[:2].upper(),
                    'username': user.user.username,
                    'points': user.points,
                    'percentage': (user.points / leaderboard[0].points) * 100
                } for user in leaderboard
            ],
            'news_items': news_items,
            'community_posts': community_posts,
        }
        return render(request, 'landing_page.html', context)
    else:
        return redirect('account_login')

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