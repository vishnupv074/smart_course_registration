from django.shortcuts import render
from django.db import transaction, connection
import time

from courses.models import Section
from enrollment.models import Enrollment
from .tasks import update_section_capacity, insert_enrollment, deadlock_task_a, deadlock_task_b

def dashboard(request):
    return render(request, 'adbms/dashboard.html')

def non_repeatable_read(request):
    """
    Demonstrates Non-Repeatable Read anomaly.
    1. Transaction A reads a row.
    2. Transaction B (Celery task) updates the row and commits.
    3. Transaction A reads the row again and sees the new value.
    This happens in READ COMMITTED isolation level.
    """
    # Ensure we have a section to test with
    section = Section.objects.first()
    if not section:
        return render(request, 'adbms/error.html', {'message': 'No sections available for demo.'})

    # Reset capacity for consistent demo
    initial_capacity = 50
    section.capacity = initial_capacity
    section.save()

    results = {
        'demo_name': 'Non-Repeatable Read',
        'isolation_level': 'READ COMMITTED (Default)',
        'section_id': section.id,
        'initial_value': initial_capacity,
        'steps': []
    }

    # Start Transaction A
    with transaction.atomic():
        # Step 1: First Read
        s1 = Section.objects.get(id=section.id)
        results['steps'].append({
            'step': 1, 
            'action': 'Read 1 (Transaction A)', 
            'value': s1.capacity,
            'time': 'T1'
        })

        # Step 2: Trigger Transaction B (Background Task)
        # We change capacity to 100
        new_capacity = 100
        update_section_capacity.delay(section.id, new_capacity, delay=1)
        results['steps'].append({
            'step': 2, 
            'action': 'Trigger Transaction B (Update to 100)', 
            'value': 'Async Task Queued',
            'time': 'T2'
        })

        # Sleep to allow Transaction B to complete
        time.sleep(3)

        # Step 3: Second Read
        # In READ COMMITTED, this should see the new value (100)
        # In REPEATABLE READ, this should see the old value (50)
        s2 = Section.objects.get(id=section.id)
        results['steps'].append({
            'step': 3, 
            'action': 'Read 2 (Transaction A)', 
            'value': s2.capacity,
            'time': 'T3'
        })
        
        anomaly_detected = s1.capacity != s2.capacity
        results['anomaly_detected'] = anomaly_detected
        results['conclusion'] = "Anomaly Detected! The value changed within the same transaction." if anomaly_detected else "No Anomaly. The value remained consistent."

    return render(request, 'adbms/simulation_result.html', {'results': results})

def phantom_read(request):
    """
    Demonstrates Phantom Read anomaly.
    1. Transaction A counts rows matching a criteria.
    2. Transaction B (Celery task) inserts a new row matching criteria.
    3. Transaction A counts rows again and sees a different count.
    """
    section = Section.objects.first()
    if not section:
        return render(request, 'adbms/error.html', {'message': 'No sections available for demo.'})

    # Cleanup phantom user enrollment to ensure clean state
    Enrollment.objects.filter(student__username='phantom_user').delete()

    results = {
        'demo_name': 'Phantom Read',
        'isolation_level': 'READ COMMITTED (Default)',
        'section_id': section.id,
        'initial_value': 'N/A',
        'steps': []
    }

    with transaction.atomic():
        # Step 1: First Count
        count1 = Enrollment.objects.filter(section=section).count()
        results['steps'].append({
            'step': 1, 
            'action': 'Count Enrollments (Transaction A)', 
            'value': count1,
            'time': 'T1'
        })

        # Step 2: Trigger Transaction B
        insert_enrollment.delay(section.id, delay=1)
        results['steps'].append({
            'step': 2, 
            'action': 'Trigger Transaction B (Insert new enrollment)', 
            'value': 'Async Task Queued',
            'time': 'T2'
        })

        # Sleep to allow Transaction B to complete
        time.sleep(3)

        # Step 3: Second Count
        count2 = Enrollment.objects.filter(section=section).count()
        results['steps'].append({
            'step': 3, 
            'action': 'Count Enrollments Again (Transaction A)', 
            'value': count2,
            'time': 'T3'
        })
        
        anomaly_detected = count1 != count2
        results['anomaly_detected'] = anomaly_detected
        results['conclusion'] = "Anomaly Detected! A new 'phantom' row appeared within the same transaction." if anomaly_detected else "No Anomaly. The count remained consistent."

    return render(request, 'adbms/simulation_result.html', {'results': results})


def deadlock_simulation(request):
    """
    Demonstrates Deadlock.
    Triggers two background tasks that try to acquire locks in reverse order.
    """
    # Ensure we have two sections
    s1 = Section.objects.first()
    s2 = Section.objects.exclude(id=s1.id).first()
    
    if not s1 or not s2:
        # Create a second section if needed
        from users.models import User
        from courses.models import Course
        instructor = User.objects.filter(role='INSTRUCTOR').first()
        course = Course.objects.first()
        if not instructor or not course:
             return render(request, 'adbms/error.html', {'message': 'Not enough data for deadlock demo.'})
             
        s2 = Section.objects.create(
            course=course, 
            instructor=instructor, 
            semester='Spring 2026', 
            capacity=30, 
            room_number='102', 
            schedule='Tue 10am'
        )

    results = {
        'demo_name': 'Deadlock Simulation',
        'isolation_level': 'READ COMMITTED (Default)',
        'section_id': f"{s1.id} & {s2.id}",
        'initial_value': 'N/A',
        'steps': []
    }

    # We trigger both tasks almost simultaneously
    # Task A: Locks S1, waits, wants S2
    # Task B: Locks S2, waits, wants S1
    
    task_a = deadlock_task_a.delay(s1.id, s2.id)
    results['steps'].append({
        'step': 1, 
        'action': 'Trigger Task A (Locks S1, wants S2)', 
        'value': f'Task ID: {task_a.id}',
        'time': 'T1'
    })

    task_b = deadlock_task_b.delay(s1.id, s2.id)
    results['steps'].append({
        'step': 2, 
        'action': 'Trigger Task B (Locks S2, wants S1)', 
        'value': f'Task ID: {task_b.id}',
        'time': 'T1'
    })

    results['steps'].append({
        'step': 3, 
        'action': 'Wait for Deadlock Resolution', 
        'value': 'Check Celery Logs / Monitor', 
        'time': 'T2'
    })
    
    results['anomaly_detected'] = True
    results['conclusion'] = "Deadlock Scenario Triggered! One of the tasks will be terminated by PostgreSQL's deadlock detector. Check the Celery logs to see which one failed."

    return render(request, 'adbms/simulation_result.html', {'results': results})


