from celery import shared_task
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


@shared_task
def process_waitlist(section_id):
    """
    Process waitlist for a section when a seat becomes available.
    Automatically enrolls the first student in the waitlist (FIFO order).
    
    Args:
        section_id (int): The ID of the section to process waitlist for.
        
    Returns:
        str: Status message indicating the result of the operation.
    """
    from courses.models import Section
    from .models import Enrollment, Waitlist
    
    try:
        with transaction.atomic():
            # Lock the section to prevent race conditions
            section = Section.objects.select_for_update().get(id=section_id)
            
            # Check if there are available seats
            current_enrollment = Enrollment.objects.filter(section=section).count()
            if current_enrollment >= section.capacity:
                return f"Section {section_id} is still full. No waitlist processing needed."
            
            # Get the first student in the waitlist (FIFO order)
            waitlist_entry = Waitlist.objects.filter(section=section).select_for_update().first()
            
            if not waitlist_entry:
                return f"No students in waitlist for section {section_id}."
            
            student = waitlist_entry.student
            
            # Check if student is already enrolled (safety check)
            if Enrollment.objects.filter(student=student, section=section).exists():
                # Remove from waitlist and continue
                waitlist_entry.delete()
                return f"Student {student.username} was already enrolled. Removed from waitlist."
            
            # Check for schedule conflicts
            from enrollment.views import EnrollStudentView
            view = EnrollStudentView()
            new_schedule = view.parse_schedule(section.schedule)
            
            if new_schedule:
                existing_enrollments = Enrollment.objects.filter(
                    student=student,
                    section__semester=section.semester
                ).select_related('section')
                
                for enrollment in existing_enrollments:
                    existing_schedule = view.parse_schedule(enrollment.section.schedule)
                    if view.check_conflict(new_schedule, existing_schedule):
                        # Schedule conflict - remove from waitlist and notify
                        waitlist_entry.delete()
                        logger.warning(
                            f"Schedule conflict for {student.username} in section {section_id}. "
                            f"Conflict with {enrollment.section.course.code}. Removed from waitlist."
                        )
                        
                        # Send notification email
                        send_mail(
                            subject=f'Waitlist Update: Schedule Conflict - {section.course.code}',
                            message=(
                                f'Dear {student.get_full_name() or student.username},\n\n'
                                f'A seat became available in {section.course.code} ({section.semester}), '
                                f'but we could not enroll you due to a schedule conflict with '
                                f'{enrollment.section.course.code} ({enrollment.section.schedule}).\n\n'
                                f'You have been removed from the waitlist. If you would like to enroll, '
                                f'please drop the conflicting course first.\n\n'
                                f'Best regards,\nSmart Course Registration System'
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[student.email],
                            fail_silently=True,
                        )
                        
                        return f"Schedule conflict for {student.username}. Removed from waitlist and notified."
            
            # Enroll the student
            Enrollment.objects.create(student=student, section=section)
            
            # Remove from waitlist
            waitlist_entry.delete()
            
            # Send notification email
            send_mail(
                subject=f'Enrolled from Waitlist: {section.course.code}',
                message=(
                    f'Dear {student.get_full_name() or student.username},\n\n'
                    f'Great news! A seat became available and you have been automatically enrolled in:\n\n'
                    f'Course: {section.course.code} - {section.course.title}\n'
                    f'Section: {section.semester} (Sec {section.id})\n'
                    f'Schedule: {section.schedule}\n'
                    f'Room: {section.room_number}\n'
                    f'Instructor: {section.instructor.get_full_name() if section.instructor else "TBA"}\n\n'
                    f'You can view your enrollment at: http://localhost:8000/my-enrollments/\n\n'
                    f'Best regards,\nSmart Course Registration System'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True,
            )
            
            logger.info(f"Successfully enrolled {student.username} from waitlist into section {section_id}")
            
            return f"Successfully enrolled {student.username} from waitlist into section {section_id}."
            
    except Section.DoesNotExist:
        logger.error(f"Section {section_id} not found")
        return f"Section {section_id} not found."
    except Exception as e:
        logger.error(f"Error processing waitlist for section {section_id}: {str(e)}")
        return f"Error processing waitlist: {str(e)}"


@shared_task
def notify_waitlist_position_change(section_id):
    """
    Notify all students in a waitlist about their updated position.
    This can be called when someone leaves the waitlist.
    
    Args:
        section_id (int): The ID of the section.
    """
    from courses.models import Section
    from .models import Waitlist
    
    try:
        section = Section.objects.get(id=section_id)
        waitlist_entries = Waitlist.objects.filter(section=section).select_related('student')
        
        for entry in waitlist_entries:
            position = entry.get_position()
            send_mail(
                subject=f'Waitlist Position Update: {section.course.code}',
                message=(
                    f'Dear {entry.student.get_full_name() or entry.student.username},\n\n'
                    f'Your position in the waitlist for {section.course.code} ({section.semester}) '
                    f'has been updated.\n\n'
                    f'Current Position: #{position}\n'
                    f'Total in Waitlist: {waitlist_entries.count()}\n\n'
                    f'You will be automatically enrolled when a seat becomes available.\n\n'
                    f'Best regards,\nSmart Course Registration System'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[entry.student.email],
                fail_silently=True,
            )
        
        return f"Notified {waitlist_entries.count()} students about position changes."
        
    except Section.DoesNotExist:
        return f"Section {section_id} not found."
    except Exception as e:
        logger.error(f"Error notifying waitlist for section {section_id}: {str(e)}")
        return f"Error: {str(e)}"
