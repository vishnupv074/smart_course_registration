from django.db import connection
from django.utils import timezone
from datetime import timedelta
import redis
from django.conf import settings


def check_database_health():
    """
    Check database connectivity and response time.
    Returns: dict with 'status' (bool) and 'response_time' (float in ms)
    """
    try:
        start_time = timezone.now()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        end_time = timezone.now()
        response_time = (end_time - start_time).total_seconds() * 1000
        return {
            'status': True,
            'response_time': round(response_time, 2),
            'message': 'Database is healthy'
        }
    except Exception as e:
        return {
            'status': False,
            'response_time': None,
            'message': f'Database error: {str(e)}'
        }


def check_celery_health():
    """
    Check Redis/Celery connectivity and queue depth.
    Returns: dict with 'status' (bool) and 'queue_depth' (int)
    """
    try:
        # Parse Redis URL from Celery broker URL
        broker_url = settings.CELERY_BROKER_URL
        
        # Connect to Redis
        r = redis.from_url(broker_url)
        
        # Test connection
        r.ping()
        
        # Get queue depth (default queue is 'celery')
        queue_depth = r.llen('celery')
        
        return {
            'status': True,
            'queue_depth': queue_depth,
            'message': 'Task queue is healthy'
        }
    except Exception as e:
        return {
            'status': False,
            'queue_depth': None,
            'message': f'Task queue error: {str(e)}'
        }


def get_enrollment_trends(days=30):
    """
    Get daily enrollment counts for the last N days.
    Returns: list of dicts with 'date' and 'count'
    """
    from enrollment.models import Enrollment
    from django.db.models import Count
    from django.db.models.functions import TruncDate
    
    start_date = timezone.now() - timedelta(days=days)
    
    trends = (
        Enrollment.objects
        .filter(enrolled_at__gte=start_date)
        .annotate(date=TruncDate('enrolled_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )
    
    return list(trends)


def get_popular_courses(limit=10):
    """
    Get top N courses by enrollment count.
    Returns: list of dicts with 'course_code', 'course_title', and 'enrollment_count'
    """
    from enrollment.models import Enrollment
    from django.db.models import Count
    
    popular = (
        Enrollment.objects
        .values('section__course__code', 'section__course__title')
        .annotate(enrollment_count=Count('id'))
        .order_by('-enrollment_count')[:limit]
    )
    
    return [
        {
            'course_code': item['section__course__code'],
            'course_title': item['section__course__title'],
            'enrollment_count': item['enrollment_count']
        }
        for item in popular
    ]


def get_seat_utilization():
    """
    Calculate seat utilization across all sections.
    Returns: dict with 'total_seats', 'filled_seats', 'utilization_percentage'
    """
    from courses.models import Section
    from enrollment.models import Enrollment
    from django.db.models import Count, Sum
    
    sections = Section.objects.annotate(
        enrolled_count=Count('enrollments')
    ).aggregate(
        total_capacity=Sum('capacity'),
        total_enrolled=Sum('enrolled_count')
    )
    
    total_seats = sections['total_capacity'] or 0
    filled_seats = sections['total_enrolled'] or 0
    utilization = (filled_seats / total_seats * 100) if total_seats > 0 else 0
    
    return {
        'total_seats': total_seats,
        'filled_seats': filled_seats,
        'utilization_percentage': round(utilization, 2)
    }
