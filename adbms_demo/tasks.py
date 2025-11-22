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
    Used to simulate concurrent updates for isolation level demos.
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
