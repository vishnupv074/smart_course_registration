from rest_framework import viewsets, permissions, status, views
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Enrollment, Waitlist
from .serializers import EnrollmentSerializer, WaitlistSerializer
from courses.models import Section
from .tasks import process_waitlist

@login_required
def my_enrollments(request):
    """
    Displays the list of courses the current student is enrolled in.
    Includes instructor details, drop functionality, and waitlist entries.
    """
    enrollments = Enrollment.objects.filter(student=request.user).select_related('section', 'section__course', 'section__instructor')
    waitlists = Waitlist.objects.filter(student=request.user).select_related('section', 'section__course', 'section__instructor')
    context = {
        'enrollments': enrollments,
        'waitlists': waitlists,
    }
    return render(request, 'enrollment/my_enrollments.html', context)

@login_required
@require_POST
def drop_course(request, section_id):
    """Drop a course (unenroll) with ACID transaction and trigger waitlist processing"""
    try:
        with transaction.atomic():
            # Get enrollment and lock it
            enrollment = get_object_or_404(
                Enrollment.objects.select_for_update(),
                student=request.user,
                section_id=section_id
            )
            
            # Delete enrollment
            enrollment.delete()
            
        # Trigger waitlist processing asynchronously (outside transaction)
        process_waitlist.delay(section_id)
        
        return JsonResponse({'status': 'success', 'message': 'Successfully dropped course'})
            
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            return Enrollment.objects.filter(student=user)
        elif user.role == 'INSTRUCTOR':
            return Enrollment.objects.filter(section__instructor=user)
        return Enrollment.objects.all()

class EnrollStudentView(views.APIView):
    """
    API endpoint for enrolling a student in a course section.
    Handles ACID transactions, capacity checks, and schedule conflict detection.
    """
    permission_classes = [permissions.IsAuthenticated]

    def parse_schedule(self, schedule_str):
        """
        Parse schedule string like "Mon/Wed 10:00-11:30" into structured data.
        Returns a list of dicts: [{'day': 'Mon', 'start': 600, 'end': 690}, ...]
        Time is converted to minutes from midnight.
        """
        try:
            parts = schedule_str.split(' ')
            days_part = parts[0]
            time_part = parts[1]
            
            days = days_part.split('/')
            start_str, end_str = time_part.split('-')
            
            def time_to_minutes(t_str):
                h, m = map(int, t_str.split(':'))
                return h * 60 + m
            
            start_min = time_to_minutes(start_str)
            end_min = time_to_minutes(end_str)
            
            parsed = []
            for day in days:
                parsed.append({
                    'day': day,
                    'start': start_min,
                    'end': end_min
                })
            return parsed
        except Exception:
            # If parsing fails, assume no conflict (or handle stricter)
            return []

    def check_conflict(self, schedule1, schedule2):
        """Check if two parsed schedules overlap"""
        for slot1 in schedule1:
            for slot2 in schedule2:
                if slot1['day'] == slot2['day']:
                    # Check time overlap: (StartA < EndB) and (EndA > StartB)
                    if slot1['start'] < slot2['end'] and slot1['end'] > slot2['start']:
                        return True
        return False

    def post(self, request):
        section_id = request.data.get('section_id')
        if not section_id:
            return Response({'error': 'Section ID required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Lock the section to prevent race conditions
                section = Section.objects.select_for_update().get(id=section_id)
                
                # Check if already enrolled
                if Enrollment.objects.filter(student=request.user, section=section).exists():
                    return Response({'error': 'Already enrolled in this section'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check if already in waitlist
                if Waitlist.objects.filter(student=request.user, section=section).exists():
                    return Response({'error': 'Already in waitlist for this section'}, status=status.HTTP_400_BAD_REQUEST)
                
                # Check capacity
                current_enrollment = Enrollment.objects.filter(section=section).count()
                if current_enrollment >= section.capacity:
                    # Section is full - add to waitlist
                    Waitlist.objects.create(student=request.user, section=section)
                    waitlist_position = Waitlist.objects.filter(section=section).count()
                    return Response({
                        'status': 'waitlisted',
                        'message': f'Section is full. You have been added to the waitlist at position {waitlist_position}.'
                    }, status=status.HTTP_201_CREATED)
                
                # Check for schedule conflicts
                new_schedule = self.parse_schedule(section.schedule)
                if new_schedule:
                    existing_enrollments = Enrollment.objects.filter(
                        student=request.user,
                        section__semester=section.semester  # Only check conflicts in same semester
                    ).select_related('section')
                    
                    for enrollment in existing_enrollments:
                        existing_schedule = self.parse_schedule(enrollment.section.schedule)
                        if self.check_conflict(new_schedule, existing_schedule):
                            return Response({
                                'error': f"Schedule conflict with {enrollment.section.course.code} ({enrollment.section.schedule})"
                            }, status=status.HTTP_400_BAD_REQUEST)

                # Create enrollment
                Enrollment.objects.create(student=request.user, section=section)
                
                return Response({'status': 'enrolled'}, status=status.HTTP_201_CREATED)

        except Section.DoesNotExist:
            return Response({'error': 'Section not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@login_required
def my_waitlists(request):
    """
    Displays the list of courses the current student is waitlisted for.
    Shows waitlist position and allows leaving the waitlist.
    """
    waitlists = Waitlist.objects.filter(student=request.user).select_related(
        'section', 'section__course', 'section__instructor'
    )
    
    # Add position to each waitlist entry
    waitlist_data = []
    for waitlist in waitlists:
        waitlist_data.append({
            'waitlist': waitlist,
            'position': waitlist.get_position(),
            'total': Waitlist.objects.filter(section=waitlist.section).count()
        })
    
    context = {
        'waitlist_data': waitlist_data
    }
    return render(request, 'enrollment/my_waitlists.html', context)


@login_required
@require_POST
def leave_waitlist(request, waitlist_id):
    """Remove student from waitlist"""
    try:
        with transaction.atomic():
            waitlist = get_object_or_404(
                Waitlist.objects.select_for_update(),
                id=waitlist_id,
                student=request.user
            )
            waitlist.delete()
            
        return JsonResponse({'status': 'success', 'message': 'Successfully left waitlist'})
        
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class WaitlistViewSet(viewsets.ReadOnlyModelViewSet):
    """API ViewSet for waitlist entries"""
    serializer_class = WaitlistSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            return Waitlist.objects.filter(student=user)
        elif user.role == 'INSTRUCTOR':
            return Waitlist.objects.filter(section__instructor=user)
        return Waitlist.objects.all()

