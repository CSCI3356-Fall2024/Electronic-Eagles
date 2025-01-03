"""
URL configuration for delivery3 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from app import views

urlpatterns = [
    path('actions', views.actions_view, name='actions'),
    path('activity/', views.activity_view, name='activity'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', views.landing_page, name='landing_page'),
    path('profile-setup/', views.profile_setup, name='profile_setup'),
    path('profile/', views.profile_view, name='profile'),
    path('logout/', views.logout_view, name='logout'),
    path('campaign/create/', views.campaign_create_view, name='campaign_create'),
    path('campaign', views.active_campaigns_view, name='active_campaigns'),
    path('campaigns/edit/<int:pk>/', views.edit_campaign_view, name='edit_campaign'),
    path('change_admin_status/', views.change_admin_status, name='change_admin_status'),
    path('campaign/<int:pk>/view/', views.view_campaign_details, name='view_campaign_details'),
    path('news', views.active_news_view, name='active_news'),
    path('news/create/', views.news_create_view, name='news_create'),
    path('news/edit/<int:pk>/', views.edit_news_view, name='edit_news'),
    path('rewards/', views.rewards_view, name='rewards'),
    path('validate-campaign/<uuid:campaign_id>/', views.validate_campaign, name='validate_campaign'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
