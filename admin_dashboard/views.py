from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count

from users.models import User
from courses.models import Course, Section
from enrollment.models import Enrollment
from .utils import (
    check_database_health,
    check_celery_health,
    get_enrollment_trends,
    get_popular_courses,
    get_seat_utilization
)


@login_required
def admin_dashboard(request):
    """
    Main admin dashboard view with analytics, statistics, and system health.
    Only accessible to users with ADMIN role.
    """
    # Check if user is admin
    if request.user.role != 'ADMIN':
        messages.error(request, 'Admin access required.')
        return redirect('home')
    
    # Statistics
    total_students = User.objects.filter(role='STUDENT').count()
    total_instructors = User.objects.filter(role='INSTRUCTOR').count()
    total_courses = Course.objects.count()
    total_sections = Section.objects.count()
    
    # Daily registrations (enrollments created today)
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    daily_registrations = Enrollment.objects.filter(enrolled_at__gte=today_start).count()
    
    # Total enrollments
    total_enrollments = Enrollment.objects.count()
    
    # Analytics
    enrollment_trends = get_enrollment_trends(days=30)
    popular_courses = get_popular_courses(limit=10)
    seat_utilization = get_seat_utilization()
    
    # System Health
    db_health = check_database_health()
    celery_health = check_celery_health()
    
    # Recent enrollments
    recent_enrollments = (
        Enrollment.objects
        .select_related('student', 'section__course')
        .order_by('-enrolled_at')[:10]
    )
    
    # Last enrollment timestamp
    last_enrollment = Enrollment.objects.order_by('-enrolled_at').first()
    last_enrollment_time = last_enrollment.enrolled_at if last_enrollment else None
    
    context = {
        'statistics': {
            'total_students': total_students,
            'total_instructors': total_instructors,
            'total_courses': total_courses,
            'total_sections': total_sections,
            'daily_registrations': daily_registrations,
            'total_enrollments': total_enrollments,
        },
        'analytics': {
            'enrollment_trends': enrollment_trends,
            'popular_courses': popular_courses,
            'seat_utilization': seat_utilization,
        },
        'system_health': {
            'database': db_health,
            'celery': celery_health,
            'last_enrollment_time': last_enrollment_time,
        },
        'recent_enrollments': recent_enrollments,
    }
    
    return render(request, 'admin_dashboard/dashboard.html', context)
