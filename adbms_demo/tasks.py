from celery import shared_task
from django.db import transaction
import time
from django.db import transaction
import time
from courses.models import Section
from enrollment.models import Enrollment
from django.contrib.auth import get_user_model

User = get_user_model()

@shared_task
def insert_enrollment(section_id, delay=2):
    """
    Inserts a new enrollment for a section after a delay.
    Used to simulate Phantom Read.
    
    Args:
        section_id (int): The ID of the section to enroll in.
        delay (int): Seconds to wait before inserting (to allow Transaction A to start).
    """
    time.sleep(delay)
    try:
        section = Section.objects.get(id=section_id)
        # Create a dummy user for this demo if needed, or use an existing one
        # For simplicity, we'll create a temporary user or use a specific demo user
        user, _ = User.objects.get_or_create(username='phantom_user', defaults={'role': 'STUDENT'})
        
        # Ensure unique enrollment
        if not Enrollment.objects.filter(student=user, section=section).exists():
            Enrollment.objects.create(student=user, section=section)
            return f"Inserted enrollment for user {user.username} in section {section_id}"
        return f"User {user.username} already enrolled in section {section_id}"
    except Section.DoesNotExist:
        return f"Section {section_id} not found"

@shared_task
def deadlock_task_a(section_id_1, section_id_2):
    """
    Simulates Transaction A for Deadlock.
    Locks Section 1, sleeps, then tries to lock Section 2.
    
    Logic:
    1. Start Transaction.
    2. Acquire Lock on S1 (select_for_update).
    3. Sleep (Wait for Task B to lock S2).
    4. Try to Acquire Lock on S2.
       - If Task B holds S2, this waits.
       - If Task B also tries to lock S1 (which we hold), a Deadlock occurs.
    """
    try:
        with transaction.atomic():
            # Lock Section 1
            Section.objects.select_for_update().get(id=section_id_1)
            time.sleep(2) # Wait for Task B to lock Section 2
            # Try to Lock Section 2 (Will block or deadlock)
            Section.objects.select_for_update().get(id=section_id_2)
            return "Task A completed successfully"
    except Exception as e:
        return f"Task A failed: {str(e)}"

@shared_task
def deadlock_task_b(section_id_1, section_id_2):
    """
    Simulates Transaction B for Deadlock.
    Locks Section 2, sleeps, then tries to lock Section 1.
    
    Logic:
    1. Start Transaction.
    2. Acquire Lock on S2 (select_for_update).
    3. Sleep (Wait for Task A to lock S1).
    4. Try to Acquire Lock on S1.
       - If Task A holds S1, this waits.
       - If Task A also tries to lock S2 (which we hold), a Deadlock occurs.
    """
    try:
        with transaction.atomic():
            # Lock Section 2
            Section.objects.select_for_update().get(id=section_id_2)
            time.sleep(2) # Wait for Task A to lock Section 1
            # Try to Lock Section 1 (Will block or deadlock)
            Section.objects.select_for_update().get(id=section_id_1)
            return "Task B completed successfully"
    except Exception as e:
        return f"Task B failed: {str(e)}"

@shared_task
def update_section_capacity(section_id, new_capacity, delay=2):
    """
    Updates a section's capacity after a delay.
    Used to simulate concurrent updates for isolation level demos (Non-Repeatable Read).
    
    Args:
        section_id (int): ID of the section to update.
        new_capacity (int): The new capacity value.
        delay (int): Seconds to wait before updating.
    """
    time.sleep(delay)
    try:
        section = Section.objects.get(id=section_id)
        old_capacity = section.capacity
        section.capacity = new_capacity
        section.save()
        return f"Updated section {section_id} capacity from {old_capacity} to {new_capacity}"
    except Section.DoesNotExist:
        return f"Section {section_id} not found"


@shared_task
def attempt_booking_task(section_id, delay=1):
    """
    Simulates a concurrent booking attempt (Transaction B).
    Tries to book a seat in the given section.
    """
    time.sleep(delay)
    try:
        with transaction.atomic():
            # Try to acquire lock - will block if Transaction A has it
            section = Section.objects.select_for_update().get(id=section_id)
            
            if section.capacity > 0:
                section.capacity -= 1
                section.save()
                return "Booking Successful (Transaction B)"
            else:
                return "Booking Failed: No seats left (Transaction B)"
    except Exception as e:
        return f"Booking Failed: {str(e)}"
