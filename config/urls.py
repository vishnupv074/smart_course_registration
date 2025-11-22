"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from .views import home
from users.views import register
from courses.views import (
    course_list, instructor_dashboard, 
    create_course, edit_course, 
    create_section, edit_section,
    view_section_students
)
from enrollment.views import my_enrollments

urlpatterns = [
    path('', home, name='home'),
    path('courses/', course_list, name='courses'),  # Renamed from 'course-list' to avoid API conflict
    path('instructor/dashboard/', instructor_dashboard, name='instructor-dashboard'),
    path('instructor/courses/create/', create_course, name='create-course'),
    path('instructor/courses/<int:pk>/edit/', edit_course, name='edit-course'),
    path('instructor/sections/create/', create_section, name='create-section'),
    path('instructor/sections/<int:pk>/edit/', edit_section, name='edit-section'),
    path('instructor/sections/<int:pk>/students/', view_section_students, name='view-section-students'),
    path('my-enrollments/', my_enrollments, name='my-enrollments'),
    path('register/', register, name='register'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('admin/', admin.site.urls),
    path('api/users/', include('users.urls')),
    path('api/', include('courses.urls')),
    path('api/', include('enrollment.urls')),
    path('adbms/', include('adbms_demo.urls')),
    
    # API Schema & Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
