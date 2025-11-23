from django.shortcuts import render
from django.db import transaction, connection
import time

from courses.models import Section
from enrollment.models import Enrollment
from .tasks import update_section_capacity, insert_enrollment, deadlock_task_a, deadlock_task_b, attempt_booking_task
from .models import NonPartitionedEnrollment, PartitionedEnrollment
import random

def dashboard(request):
    return render(request, 'adbms/dashboard.html')

def non_repeatable_read(request):
    """
    Demonstrates the 'Non-Repeatable Read' anomaly.
    
    THEORY:
    A Non-Repeatable Read occurs when a transaction reads the same row twice but gets different data each time.
    This happens because another concurrent transaction modified and committed the data between the two reads.
    This anomaly is possible in the 'READ COMMITTED' isolation level (PostgreSQL default).
    
    SIMULATION STEPS:
    1. Transaction A (this view) starts an atomic block (transaction).
    2. Transaction A reads the Section capacity (Read 1).
    3. Transaction A triggers a background Celery task (Transaction B).
    4. Transaction B updates the same Section's capacity and commits.
    5. Transaction A waits for B to finish.
    6. Transaction A reads the Section capacity again (Read 2).
    
    EXPECTED RESULT:
    In READ COMMITTED, Read 2 will show the new value committed by Transaction B, differing from Read 1.
    """
    # Ensure we have a section to test with
    section = Section.objects.first()
    if not section:
        return render(request, 'adbms/error.html', {'message': 'No sections available for demo.'})

    # Reset capacity to a known state (50) for consistent demo results
    initial_capacity = 50
    section.capacity = initial_capacity
    section.save()

    results = {
        'demo_name': 'Non-Repeatable Read',
        'description': 'A Non-Repeatable Read occurs when a transaction reads the same row twice but gets different data each time. This happens because another concurrent transaction modified and committed the data between the two reads.',
        'isolation_level': 'READ COMMITTED (Default)',
        'section_id': section.id,
        'initial_value': initial_capacity,
        'steps': []
    }

    # Start Transaction A
    # atomic() ensures all database operations inside this block are part of a single transaction.
    with transaction.atomic():
        # Step 1: First Read
        # We fetch the current state of the section.
        s1 = Section.objects.get(id=section.id)
        results['steps'].append({
            'step': 1, 
            'action': 'Read 1 (Transaction A)', 
            'value': s1.capacity,
            'time': 'T1'
        })

        # Step 2: Trigger Transaction B (Background Task)
        # We queue a Celery task that will run in a separate transaction (Transaction B).
        # We pass a delay to ensure it runs *after* our first read but *before* our second read.
        new_capacity = 100
        update_section_capacity.delay(section.id, new_capacity, delay=1)
        results['steps'].append({
            'step': 2, 
            'action': 'Trigger Transaction B (Update to 100)', 
            'value': 'Async Task Queued',
            'time': 'T2'
        })

        # Sleep to allow Transaction B to complete its update and commit.
        # In a real scenario, this delay represents processing time or network latency.
        time.sleep(3)

        # Step 3: Second Read
        # We fetch the section again within the SAME transaction (Transaction A).
        # In READ COMMITTED, this query sees data committed by other transactions (Transaction B).
        # Therefore, s2.capacity will be 100.
        # If we were using REPEATABLE READ, s2.capacity would still be 50.
        s2 = Section.objects.get(id=section.id)
        results['steps'].append({
            'step': 3, 
            'action': 'Read 2 (Transaction A)', 
            'value': s2.capacity,
            'time': 'T3'
        })
        
        # Check if the value changed
        anomaly_detected = s1.capacity != s2.capacity
        results['anomaly_detected'] = anomaly_detected
        results['conclusion'] = "Anomaly Detected! The value changed within the same transaction." if anomaly_detected else "No Anomaly. The value remained consistent."

    return render(request, 'adbms/simulation_result.html', {'results': results})

def phantom_read(request):
    """
    Demonstrates the 'Phantom Read' anomaly.
    
    THEORY:
    A Phantom Read occurs when a transaction executes a query returning a set of rows that satisfy a search condition,
    but a concurrent transaction inserts a new row that matches the condition.
    If the first transaction repeats the query, it sees the "phantom" row (a row that wasn't there before).
    
    SIMULATION STEPS:
    1. Transaction A (this view) counts the number of enrollments for a section.
    2. Transaction A triggers a background Celery task (Transaction B).
    3. Transaction B inserts a NEW enrollment for that section and commits.
    4. Transaction A counts the enrollments again.
    
    EXPECTED RESULT:
    In READ COMMITTED, the second count will be higher than the first, revealing the "phantom" record.
    """
    section = Section.objects.first()
    if not section:
        return render(request, 'adbms/error.html', {'message': 'No sections available for demo.'})

    # Cleanup phantom user enrollment to ensure clean state for the demo
    Enrollment.objects.filter(student__username='phantom_user').delete()

    results = {
        'demo_name': 'Phantom Read',
        'description': 'A Phantom Read occurs when a transaction executes a query returning a set of rows that satisfy a search condition, but a concurrent transaction inserts a new row that matches the condition. If the first transaction repeats the query, it sees the "phantom" row.',
        'isolation_level': 'READ COMMITTED (Default)',
        'section_id': section.id,
        'initial_value': 'N/A',
        'steps': []
    }

    with transaction.atomic():
        # Step 1: First Count
        # We count how many students are currently enrolled.
        count1 = Enrollment.objects.filter(section=section).count()
        results['steps'].append({
            'step': 1, 
            'action': 'Count Enrollments (Transaction A)', 
            'value': count1,
            'time': 'T1'
        })

        # Step 2: Trigger Transaction B
        # Queue a task to insert a new enrollment record.
        insert_enrollment.delay(section.id, delay=1)
        results['steps'].append({
            'step': 2, 
            'action': 'Trigger Transaction B (Insert new enrollment)', 
            'value': 'Async Task Queued',
            'time': 'T2'
        })

        # Sleep to allow Transaction B to complete the insertion.
        time.sleep(3)

        # Step 3: Second Count
        # We run the SAME count query again.
        # In READ COMMITTED, this query sees the new row inserted by Transaction B.
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
    Demonstrates a Database Deadlock.
    
    THEORY:
    A Deadlock occurs when two transactions are waiting for each other to give up locks.
    Transaction A holds Lock 1 and waits for Lock 2.
    Transaction B holds Lock 2 and waits for Lock 1.
    Neither can proceed, creating a cycle.
    
    SIMULATION STEPS:
    1. We identify two resources (Section 1 and Section 2).
    2. We trigger two background tasks (Task A and Task B) simultaneously.
    3. Task A: Locks Section 1 -> Sleeps -> Tries to Lock Section 2.
    4. Task B: Locks Section 2 -> Sleeps -> Tries to Lock Section 1.
    
    EXPECTED RESULT:
    PostgreSQL's deadlock detector will identify the circular wait and forcibly terminate one of the transactions
    to allow the other to proceed. The terminated transaction will raise a DeadlockDetected exception.
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
        'description': 'A Deadlock occurs when two transactions are waiting for each other to give up locks. Transaction A holds Lock 1 and waits for Lock 2, while Transaction B holds Lock 2 and waits for Lock 1.',
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

    results['conclusion'] = "Deadlock Scenario Triggered! One of the tasks will be terminated by PostgreSQL's deadlock detector. Check the Celery logs to see which one failed."

    return render(request, 'adbms/simulation_result.html', {'results': results})


def indexing_benchmark(request):
    """
    Benchmarks query performance with and without indexes.
    
    THEORY:
    Indexes are data structures (like B-Trees) that allow the database to find rows efficiently (O(log N))
    without scanning the entire table (O(N)).
    
    SIMULATION STEPS:
    1. We execute a query searching for a substring in 'description' (Unindexed).
       - This forces a Sequential Scan (checking every row).
    2. We execute a query searching for a specific 'code' (Indexed).
       - This allows an Index Scan (jumping to the row).
    3. We use 'EXPLAIN (ANALYZE, FORMAT JSON)' to get the actual execution time from PostgreSQL.
    """
    # We will query by 'title' which is currently not indexed (only ID and Code are usually indexed by default or unique constraints)
    # Actually, let's check if we want to add an index dynamically or just show the difference
    # For this demo, we'll assume 'description' is NOT indexed.
    
    search_term = "Description"
    
    results = {
        'demo_name': 'Indexing Benchmark',
        'scenarios': []
    }

    # Scenario 1: No Index (Seq Scan) on Description
    # We'll search for a substring in description.
    # Since there is no index on the 'description' column, Postgres must check every single row.
    query = "SELECT * FROM courses_course WHERE description LIKE %s"
    param = f"%{search_term}%"
    
    with connection.cursor() as cursor:
        # EXPLAIN ANALYZE runs the query and returns performance statistics.
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query, [param])
        explain_output = cursor.fetchone()[0][0]
        
        results['scenarios'].append({
            'name': 'No Index (Sequential Scan)',
            'query': f"SELECT * FROM courses_course WHERE description LIKE '%{search_term}%'",
            # Rounding to 3 decimal places for readability
            'execution_time': round(explain_output['Execution Time'], 3),
            'plan': explain_output['Plan']['Node Type'],
            'details': explain_output
        })

    # Scenario 2: B-Tree Index on Code (Indexed by unique constraint)
    # We'll search for a specific code.
    # The 'code' column has a UNIQUE constraint, which automatically creates a B-Tree index.
    target_code = "CS050000"
    query_index = "SELECT * FROM courses_course WHERE code = %s"
    
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query_index, [target_code])
        explain_output = cursor.fetchone()[0][0]
        
        results['scenarios'].append({
            'name': 'B-Tree Index (Index Scan)',
            'query': f"SELECT * FROM courses_course WHERE code = '{target_code}'",
            'execution_time': round(explain_output['Execution Time'], 3),
            'plan': explain_output['Plan']['Node Type'],
            'details': explain_output
        })

    return render(request, 'adbms/indexing_result.html', {'results': results})




def query_optimization(request):
    """
    Visualizes Query Optimization using EXPLAIN ANALYZE.
    Allows users to input SQL queries and see the execution plan and cost.
    """
    default_query = "SELECT * FROM courses_course WHERE code = 'CS101'"
    query = request.POST.get('query', default_query)
    results = None
    error = None

    if request.method == 'POST':
        try:
            # Basic validation for demo safety
            if not query.strip().lower().startswith('select'):
                raise Exception("Only SELECT queries are allowed for this demo.")

            with connection.cursor() as cursor:
                # Run EXPLAIN ANALYZE
                cursor.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")
                explain_output = cursor.fetchone()[0][0]
            
            results = {
                'query': query,
                'execution_time': round(explain_output.get('Execution Time', 0), 3),
                'planning_time': round(explain_output.get('Planning Time', 0), 3),
                'total_cost': explain_output['Plan']['Total Cost'],
                'plan_node': explain_output['Plan']['Node Type'],
                'full_plan': explain_output
            }
        except Exception as e:
            error = str(e)

    return render(request, 'adbms/query_optimization.html', {
        'query': query,
        'results': results,
        'error': error
    })


def partitioning_demo(request):
    """
    Demonstrates the performance benefits of Table Partitioning.
    
    THEORY:
    Partitioning splits a large table into smaller, more manageable pieces (partitions).
    When querying with a filter on the partition key (e.g., semester), the database can
    "prune" irrelevant partitions, scanning only the necessary child table.
    
    SIMULATION STEPS:
    1. Populate both tables with dummy data (if empty).
    2. Query Non-Partitioned Table for 'Fall 2024'.
       - Expect: Sequential Scan on the entire huge table.
    3. Query Partitioned Table for 'Fall 2024'.
       - Expect: Sequential Scan ONLY on the 'fall2024' partition.
    """
    # 1. Populate Data if needed
    if NonPartitionedEnrollment.objects.count() < 1000:
        # Generate dummy data
        semesters = ['Fall 2024', 'Spring 2025', 'Fall 2025', 'Spring 2026']
        batch_size = 5000
        
        objs_non = []
        objs_part = []
        
        for i in range(batch_size * 4): # 20k rows total
            sem = random.choice(semesters)
            name = f"Student {i}"
            code = f"CS{random.randint(100, 999)}"
            grade = random.choice(['A', 'B', 'C', 'D', 'F'])
            
            objs_non.append(NonPartitionedEnrollment(
                student_name=name, course_code=code, semester=sem, grade=grade
            ))
            objs_part.append(PartitionedEnrollment(
                student_name=name, course_code=code, semester=sem, grade=grade
            ))
            
        NonPartitionedEnrollment.objects.bulk_create(objs_non)
        PartitionedEnrollment.objects.bulk_create(objs_part)

    results = {
        'demo_name': 'Partitioning Benchmark',
        'scenarios': []
    }
    
    target_semester = 'Fall 2024'
    
    # Scenario 1: Non-Partitioned Table
    query_non = "SELECT * FROM adbms_demo_nonpartitionedenrollment WHERE semester = %s"
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query_non, [target_semester])
        explain_output = cursor.fetchone()[0][0]
        
        results['scenarios'].append({
            'name': 'Non-Partitioned Table',
            'query': f"SELECT * FROM non_partitioned WHERE semester = '{target_semester}'",
            'execution_time': round(explain_output['Execution Time'], 3),
            'plan': explain_output['Plan']['Node Type'],
            'details': explain_output
        })

    # Scenario 2: Partitioned Table
    query_part = "SELECT * FROM adbms_demo_partitionedenrollment WHERE semester = %s"
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query_part, [target_semester])
        explain_output = cursor.fetchone()[0][0]
        
        results['scenarios'].append({
            'name': 'Partitioned Table (Pruning)',
            'query': f"SELECT * FROM partitioned WHERE semester = '{target_semester}'",
            'execution_time': round(explain_output['Execution Time'], 3),
            'plan': explain_output['Plan']['Node Type'], # Might show Append or Seq Scan on child
            'details': explain_output
        })

    return render(request, 'adbms/partitioning_result.html', {'results': results})


def row_locking_demo(request):
    """
    Demonstrates Row Locking (SELECT FOR UPDATE).
    
    THEORY:
    SELECT FOR UPDATE locks the selected rows, preventing other transactions from modifying
    or locking them until the current transaction ends. This is crucial for preventing
    race conditions (e.g., double booking).
    
    SIMULATION STEPS:
    1. Reset Section capacity to 1.
    2. Transaction A (User) starts, locks the row.
    3. Transaction B (Background) starts, tries to lock the same row.
    4. Transaction B blocks/waits.
    5. Transaction A books the seat and commits.
    6. Transaction B unblocks, sees 0 capacity, and fails gracefully.
    """
    section = Section.objects.first()
    if not section:
        return render(request, 'adbms/error.html', {'message': 'No sections available for demo.'})

    # Reset capacity to 1
    section.capacity = 1
    section.save()

    results = {
        'demo_name': 'Row Locking (SELECT FOR UPDATE)',
        'description': 'Demonstrates how locking a row prevents concurrent modifications. Transaction A locks the row, forcing Transaction B to wait.',
        'section_id': section.id,
        'initial_capacity': 1,
        'steps': []
    }

    with transaction.atomic():
        # Step 1: Transaction A starts and locks the row
        # select_for_update() generates: SELECT ... FOR UPDATE
        s_locked = Section.objects.select_for_update().get(id=section.id)
        
        results['steps'].append({
            'step': 1,
            'action': 'Transaction A: Acquire Lock (SELECT FOR UPDATE)',
            'value': f'Locked Section {s_locked.id}',
            'time': 'T1'
        })

        # Step 2: Trigger Transaction B
        # This task will try to acquire the same lock and will be forced to WAIT.
        task = attempt_booking_task.delay(section.id, delay=1)
        
        results['steps'].append({
            'step': 2,
            'action': 'Transaction B: Attempt Booking (Background)',
            'value': f'Task Queued (ID: {task.id}) - Will Block',
            'time': 'T2'
        })

        # Simulate processing time for Transaction A
        # During this sleep, Transaction B is running but BLOCKED at the database level.
        time.sleep(4)

        # Step 3: Transaction A completes booking
        if s_locked.capacity > 0:
            s_locked.capacity -= 1
            s_locked.save()
            status = "Booking Successful"
        else:
            status = "Failed (No Seats)"
            
        results['steps'].append({
            'step': 3,
            'action': 'Transaction A: Book Seat & Commit',
            'value': f'{status}. Remaining Capacity: {s_locked.capacity}',
            'time': 'T3'
        })

    # After the block exits, Transaction A commits.
    # Transaction B unblocks, reads the new capacity (0), and fails.
    
    results['conclusion'] = "Transaction A successfully locked the row. Transaction B was forced to wait until A finished, preventing a race condition (Double Booking)."

    return render(request, 'adbms/simulation_result.html', {'results': results})
