from django.urls import path
from .views import (
    UserRegistrationView, UserProfileView, 
    profile, edit_profile, change_password,
    send_verification_email, verify_email
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='api-register'),
    path('profile/', UserProfileView.as_view(), name='api-profile'),
    path('my-profile/', profile, name='profile'),
    path('my-profile/edit/', edit_profile, name='edit-profile'),
    path('my-profile/change-password/', change_password, name='change-password'),
    path('my-profile/send-verification/', send_verification_email, name='send-verification'),
    path('verify-email/<str:token>/', verify_email, name='verify-email'),
]
