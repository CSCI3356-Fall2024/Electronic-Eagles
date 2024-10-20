from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from allauth.socialaccount.models import SocialAccount
from .models import UserProfile
from .forms import UserProfileForm

def google_login(request):
    return render(request, 'google_login.html')
    adapter = GoogleOAuth2Adapter(request)
    client = OAuth2Client(request)
    login_url = adapter.get_login_url(request, client)
    print(f"Redirecting to: {login_url}")  # Debug print
    return redirect(login_url)

@login_required
def profile_setup(request):
    try:
        # Check if user already has a profile
        profile = UserProfile.objects.get(user=request.user)
        return redirect('home')  # Redirect to home if profile exists
    except UserProfile.DoesNotExist:
        if request.method == 'POST':
            form = UserProfileForm(request.POST, request.FILES)
            if form.is_valid():
                profile = form.save(commit=False)
                profile.user = request.user
                profile.save()
                return redirect('home')
        else:
            form = UserProfileForm()
        
        return render(request, 'profile_setup.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('google_login')

@login_required
def profile_view(request):
    try:
        # Try to get the user's profile
        user_profile = UserProfile.objects.get(user=request.user)
        
        # Check if profile is complete (you can define what "complete" means)
        if not user_profile.school or not user_profile.graduation_year:
            return redirect('profile_setup')  # Redirect to profile setup if incomplete
        
        # Determine the user's role
        role = 'Supervisor' if user_profile.is_supervisor else 'Student'
        
        # Pass the profile and role to the template
        return render(request, 'profile.html', {'user_profile': user_profile, 'role': role})
    
    except UserProfile.DoesNotExist:
        # Redirect to profile setup if the profile doesn't exist
        return redirect('profile_setup')

def home_view(response):
    return render(response, "base.html")