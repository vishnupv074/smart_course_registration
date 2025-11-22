from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='adbms-dashboard'),
    path('non-repeatable-read/', views.non_repeatable_read, name='non-repeatable-read'),
    path('phantom-read/', views.phantom_read, name='phantom-read'),
    path('deadlock/', views.deadlock_simulation, name='deadlock'),
]
