from django.urls import path
from .views import UserRegistrationView, UserProfileView

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='api-register'),
    path('profile/', UserProfileView.as_view(), name='api-profile'),
]
