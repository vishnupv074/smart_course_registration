from django.urls import path
from .views import UserRegistrationView, UserProfileView, profile, edit_profile

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='api-register'),
    path('profile/', UserProfileView.as_view(), name='api-profile'),
    path('my-profile/', profile, name='profile'),
    path('my-profile/edit/', edit_profile, name='edit-profile'),
]
