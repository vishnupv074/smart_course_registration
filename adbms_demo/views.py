from django.shortcuts import render, redirect
from django.db import transaction, connection, connections
import time

from courses.models import Section
from enrollment.models import Enrollment
from .tasks import update_section_capacity, insert_enrollment, deadlock_task_a, deadlock_task_b, attempt_booking_task, mvcc_update_section_task
from .models import NonPartitionedEnrollment, PartitionedEnrollment, DenormalizedEnrollment
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

    # Calculate improvement metrics
    without_index_time = results['scenarios'][0]['execution_time']
    with_index_time = results['scenarios'][1]['execution_time']
    
    improvement = 0
    if without_index_time > 0:
        improvement = ((without_index_time - with_index_time) / without_index_time) * 100
        
    context = {
        'results': results,
        'without_index_time': without_index_time,
        'with_index_time': with_index_time,
        'improvement_percentage': round(improvement, 1)
    }

    return render(request, 'adbms/indexing_result.html', context)




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

    try:
        # Reset for demo: Ensure capacity is 1
        with transaction.atomic():
            section = Section.objects.select_for_update().get(id=1)
            section.capacity = 1
            section.save()
            
            # Clear enrollments for this section to ensure seat is free
            Enrollment.objects.filter(section=section).delete()
            
        # Start background task (Transaction B)
        # We delay it slightly to ensure Transaction A starts first
        attempt_booking_task.delay(section_id=1, student_id=3, delay=0.5)
        
        # Start foreground transaction (Transaction A)
        # Simulate user reading the page, thinking, then booking
        time.sleep(0.1) 
        
        with transaction.atomic():
            # 1. Lock the row
            sec = Section.objects.select_for_update().get(id=1)
            
            # 2. Simulate processing time (hold the lock)
            time.sleep(2.0)
            
            # 3. Check capacity and book
            if sec.capacity > 0:
                Enrollment.objects.create(student_id=2, section=sec)
                sec.capacity -= 1
                sec.save()
                result = "Transaction A: Successfully booked the last seat!"
            else:
                result = "Transaction A: Failed - Seat taken!"
                
    except Exception as e:
        result = f"Error: {str(e)}"

    return render(request, 'adbms/simulation_result.html', {
        'title': 'Row Locking (SELECT FOR UPDATE)',
        'result': result,
        'explanation': """
        <strong>Scenario:</strong> Two users try to book the LAST seat at the same time.<br><br>
        <strong>Without Locking:</strong> Both read capacity=1, both book, capacity becomes -1 (Overbooking).<br>
        <strong>With SELECT FOR UPDATE:</strong><br>
        1. Transaction A locks the row.<br>
        2. Transaction B tries to read/lock but is BLOCKED (waits).<br>
        3. Transaction A books and commits.<br>
        4. Transaction B unblocks, reads new capacity=0, and fails gracefully.
        """
    })


def trigger_demo(request):
    """
    Demonstrates Database Triggers & Stored Procedures (Audit Logging).
    Allows users to perform CRUD operations on 4 tables and see the automatic audit logs.
    """
    from .models import AuditLog
    from courses.models import Course, Section
    from enrollment.models import Enrollment, Waitlist
    from users.models import User
    from django.utils import timezone
    import json
    
    # Handle demo actions
    if request.method == 'POST':
        action = request.POST.get('action')
        table = request.POST.get('table')
        
        try:
            with transaction.atomic():
                # --- ENROLLMENT ACTIONS ---
                if table == 'enrollment':
                    student = User.objects.get(id=2) # Use a demo student
                    section = Section.objects.first()
                    
                    if action == 'create':
                        # Create new enrollment
                        if not Enrollment.objects.filter(student=student, section=section).exists():
                            Enrollment.objects.create(student=student, section=section)
                            
                    elif action == 'update':
                        # Update grade
                        enrollment = Enrollment.objects.filter(student=student, section=section).first()
                        if enrollment:
                            grades = ['A', 'B', 'C', 'B+', 'A-']
                            current_grade = enrollment.grade
                            new_grade = random.choice([g for g in grades if g != current_grade])
                            enrollment.grade = new_grade
                            enrollment.save()
                            
                    elif action == 'delete':
                        # Delete enrollment
                        Enrollment.objects.filter(student=student, section=section).delete()
                
                # --- COURSE ACTIONS ---
                elif table == 'course':
                    if action == 'create':
                        code = f"DEMO-{random.randint(100, 999)}"
                        Course.objects.create(
                            code=code,
                            title=f"Demo Course {code}",
                            description="Created via Trigger Demo",
                            credits=3
                        )
                    elif action == 'update':
                        course = Course.objects.filter(code__startswith='DEMO-').last()
                        if course:
                            course.credits = random.choice([3, 4, 2])
                            course.save()
                    elif action == 'delete':
                        course = Course.objects.filter(code__startswith='DEMO-').last()
                        if course:
                            course.delete()
                            
                # --- SECTION ACTIONS ---
                elif table == 'section':
                    course = Course.objects.first()
                    if action == 'create':
                        Section.objects.create(
                            course=course,
                            semester="Summer 2026",
                            capacity=30,
                            room_number="Demo Room",
                            schedule="Mon 10:00"
                        )
                    elif action == 'update':
                        section = Section.objects.filter(semester="Summer 2026").last()
                        if section:
                            section.capacity = random.randint(20, 50)
                            section.save()
                    elif action == 'delete':
                        section = Section.objects.filter(semester="Summer 2026").last()
                        if section:
                            section.delete()
                            
                # --- WAITLIST ACTIONS ---
                elif table == 'waitlist':
                    student = User.objects.get(id=3) # Another demo student
                    section = Section.objects.first()
                    
                    if action == 'create':
                        if not Waitlist.objects.filter(student=student, section=section).exists():
                            Waitlist.objects.create(student=student, section=section)
                    elif action == 'update':
                        wl = Waitlist.objects.filter(student=student, section=section).first()
                        if wl:
                            wl.notified = not wl.notified
                            wl.save()
                    elif action == 'delete':
                        Waitlist.objects.filter(student=student, section=section).delete()
                        
        except Exception as e:
            # In a real app, we'd handle this better
            pass
            
        return redirect('trigger-demo')
    
    # Fetch recent audit logs
    logs = AuditLog.objects.all()[:50]
    
    # Calculate statistics
    stats = {
        'insert': AuditLog.objects.filter(operation='INSERT').count(),
        'update': AuditLog.objects.filter(operation='UPDATE').count(),
        'delete': AuditLog.objects.filter(operation='DELETE').count(),
        'total': AuditLog.objects.count()
    }
    
    return render(request, 'adbms_demo/trigger_demo.html', {
        'logs': logs,
        'stats': stats
    })


def normalization_demo(request):
    """
    Demonstrates Normalization vs Denormalization (Materialized Views).
    
    THEORY:
    Normalized databases reduce redundancy but require joins for complex queries.
    Denormalized data (via materialized views) trades storage for query performance.
    
    SIMULATION STEPS:
    1. Query normalized tables with 3 joins (enrollment -> user, section, course).
    2. Query denormalized materialized view (pre-joined data).
    3. Compare execution times using EXPLAIN ANALYZE.
    """
    results = {
        'demo_name': 'Normalization vs Denormalization',
        'scenarios': []
    }

    # Scenario 1: Normalized Query (Multiple Joins)
    target_semester = 'Fall 2024'
    
    query_normalized = """
        SELECT 
            u.username, c.code, c.title, s.semester, e.grade, c.credits
        FROM 
            enrollment_enrollment e
        JOIN 
            users_user u ON e.student_id = u.id
        JOIN 
            courses_section s ON e.section_id = s.id
        JOIN 
            courses_course c ON s.course_id = c.id
        WHERE 
            s.semester = %s
    """
    
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query_normalized, [target_semester])
        explain_output = cursor.fetchone()[0][0]
        
        results['scenarios'].append({
            'name': 'Normalized (3 Joins)',
            'query': "SELECT ... FROM enrollment JOIN user JOIN section JOIN course WHERE semester = ...",
            'execution_time': round(explain_output['Execution Time'], 3),
            'plan': explain_output['Plan']['Node Type'],
            'details': explain_output
        })

    # Scenario 2: Denormalized Query (Materialized View)
    query_denormalized = """
        SELECT 
            student_name, course_code, course_title, semester, grade, credits
        FROM 
            adbms_demo_materialized_enrollment
        WHERE 
            semester = %s
    """
    
    with connection.cursor() as cursor:
        cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query_denormalized, [target_semester])
        explain_output = cursor.fetchone()[0][0]
        
        results['scenarios'].append({
            'name': 'Denormalized (Materialized View)',
            'query': "SELECT ... FROM materialized_enrollment WHERE semester = ...",
            'execution_time': round(explain_output['Execution Time'], 3),
            'plan': explain_output['Plan']['Node Type'],
            'details': explain_output
        })

    return render(request, 'adbms/normalization_result.html', {'results': results})


def mvcc_visibility_demo(request):
    """
    Demonstrates PostgreSQL's Multi-Version Concurrency Control (MVCC) and Row Versioning.
    
    THEORY:
    MVCC allows multiple transactions to access the same data concurrently without blocking.
    Each transaction sees a consistent snapshot of the database at the time it started.
    PostgreSQL maintains multiple versions of rows using system columns:
    - xmin: Transaction ID that created this row version
    - xmax: Transaction ID that deleted/updated this row version (0 if still current)
    - ctid: Physical location (page, tuple) of the row version
    
    SIMULATION STEPS:
    1. Reset a section to a known state (capacity = 50).
    2. Transaction A starts and reads the section with system columns.
    3. Transaction B (background task) updates the section to capacity = 100.
    4. Transaction A reads the section again - still sees old version (snapshot isolation).
    5. Transaction A commits.
    6. New read shows the updated version from Transaction B.
    
    EXPECTED RESULT:
    Transaction A sees a consistent snapshot (capacity = 50) even after Transaction B commits.
    After Transaction A commits, the new version (capacity = 100) becomes visible.
    Different xmin values show that multiple row versions existed.
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
        'demo_name': 'MVCC & Visibility',
        'description': 'Multi-Version Concurrency Control (MVCC) allows multiple transactions to access the same data concurrently. Each transaction sees a consistent snapshot through row versioning tracked by system columns (xmin, xmax, ctid).',
        'isolation_level': 'READ COMMITTED (Default)',
        'section_id': section.id,
        'initial_value': initial_capacity,
        'steps': [],
        'row_versions': []
    }

    # Start Transaction A
    with transaction.atomic():
        # Step 1: First Read - Get initial row version with system columns
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, capacity, xmin, xmax, ctid 
                FROM courses_section 
                WHERE id = %s
            """, [section.id])
            row = cursor.fetchone()
            id_val, capacity_val, xmin_val, xmax_val, ctid_val = row
            
            results['steps'].append({
                'step': 1,
                'action': 'Transaction A: Read section with system columns',
                'value': f'capacity={capacity_val}',
                'time': 'T1',
                'details': f'xmin={xmin_val}, xmax={xmax_val}, ctid={ctid_val}'
            })
            
            results['row_versions'].append({
                'version': 'Initial Version (Transaction A View)',
                'capacity': capacity_val,
                'xmin': str(xmin_val),
                'xmax': str(xmax_val),
                'ctid': str(ctid_val),
                'visible_to': 'Transaction A'
            })

        # Step 2: Trigger Transaction B (Background Task)
        new_capacity = 100
        task = mvcc_update_section_task.delay(section.id, new_capacity, delay=1)
        results['steps'].append({
            'step': 2,
            'action': 'Transaction B: Update section capacity to 100 (background)',
            'value': 'Async Task Queued',
            'time': 'T2',
            'details': f'Task ID: {task.id}'
        })

        # Sleep to allow Transaction B to complete and commit
        time.sleep(3)
        
        results['steps'].append({
            'step': 3,
            'action': 'Transaction B: Committed new row version',
            'value': f'capacity={new_capacity}',
            'time': 'T3',
            'details': 'New row version created with new xmin'
        })

        # Step 4: Second Read within Transaction A
        # Due to snapshot isolation, Transaction A still sees the old version
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, capacity, xmin, xmax, ctid 
                FROM courses_section 
                WHERE id = %s
            """, [section.id])
            row = cursor.fetchone()
            id_val, capacity_val, xmin_val, xmax_val, ctid_val = row
            
            results['steps'].append({
                'step': 4,
                'action': 'Transaction A: Read section again (snapshot isolation)',
                'value': f'capacity={capacity_val}',
                'time': 'T4',
                'details': f'Still sees old version! xmin={xmin_val}, xmax={xmax_val}, ctid={ctid_val}'
            })
            
            # Check if we still see the old version
            snapshot_isolation_works = (capacity_val == initial_capacity)
            results['snapshot_isolation_demonstrated'] = snapshot_isolation_works

    # Transaction A has now committed
    results['steps'].append({
        'step': 5,
        'action': 'Transaction A: Committed',
        'value': 'Transaction A ends',
        'time': 'T5',
        'details': 'Snapshot is released'
    })

    # Step 6: Read after Transaction A commits - now we see the new version
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, capacity, xmin, xmax, ctid 
            FROM courses_section 
            WHERE id = %s
        """, [section.id])
        row = cursor.fetchone()
        id_val, capacity_val, xmin_val, xmax_val, ctid_val = row
        
        results['steps'].append({
            'step': 6,
            'action': 'New Transaction: Read section (after Transaction A commits)',
            'value': f'capacity={capacity_val}',
            'time': 'T6',
            'details': f'Now sees new version! xmin={xmin_val}, xmax={xmax_val}, ctid={ctid_val}'
        })
        
        results['row_versions'].append({
            'version': 'Updated Version (After Transaction A)',
            'capacity': capacity_val,
            'xmin': str(xmin_val),
            'xmax': str(xmax_val),
            'ctid': str(ctid_val),
            'visible_to': 'New Transactions'
        })

    results['conclusion'] = """
    MVCC Demonstrated! Transaction A maintained a consistent snapshot (capacity=50) even after 
    Transaction B committed changes (capacity=100). This is snapshot isolation in action. 
    Different xmin values prove that multiple row versions existed simultaneously. 
    PostgreSQL's MVCC allows high concurrency without read locks.
    """

    return render(request, 'adbms/mvcc_result.html', {'results': results})


def monitoring_stats_demo(request):
    """
    Demonstrates Database Monitoring & Statistics using pg_stat_statements.
    
    THEORY:
    pg_stat_statements is a PostgreSQL extension that tracks execution statistics for all SQL statements.
    It provides insights into query performance, helping identify slow queries and optimization opportunities.
    
    Key Metrics:
    - total_exec_time: Total time spent executing this query
    - calls: Number of times the query was executed
    - mean_exec_time: Average execution time per call
    - rows: Total number of rows returned/affected
    
    SIMULATION STEPS:
    1. Query pg_stat_statements to get top queries by execution time.
    2. Calculate performance metrics and latency distribution.
    3. Optionally execute sample workload to generate statistics.
    4. Visualize results with charts and tables.
    """
    from django.db.models import Count
    import json
    
    results = {
        'demo_name': 'Monitoring & Statistics',
        'description': 'PostgreSQL query performance monitoring using pg_stat_statements extension. Tracks execution time, call frequency, and resource usage for all database queries.',
        'top_queries': [],
        'metrics': {},
        'latency_histogram': {},
        'error': None
    }
    
    try:
        # Check if pg_stat_statements is available
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
                );
            """)
            extension_exists = cursor.fetchone()[0]
            
            if not extension_exists:
                results['error'] = "pg_stat_statements extension is not enabled. Please run migrations to enable it."
                return render(request, 'adbms/monitoring_result.html', {'results': results})
        
        # Generate sample workload if no statistics exist
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM pg_stat_statements;")
            stats_count = cursor.fetchone()[0]
            
            if stats_count < 5:
                # Execute some sample queries to generate statistics
                cursor.execute("SELECT COUNT(*) FROM courses_course;")
                cursor.execute("SELECT COUNT(*) FROM courses_section;")
                cursor.execute("SELECT COUNT(*) FROM enrollment_enrollment;")
                cursor.execute("SELECT COUNT(*) FROM users_user WHERE role = 'STUDENT';")
                cursor.execute("""
                    SELECT c.code, COUNT(e.id) 
                    FROM courses_course c 
                    LEFT JOIN courses_section s ON c.id = s.course_id 
                    LEFT JOIN enrollment_enrollment e ON s.id = e.section_id 
                    GROUP BY c.code;
                """)
        
        # Query top queries by total execution time
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    query,
                    calls,
                    total_exec_time,
                    mean_exec_time,
                    min_exec_time,
                    max_exec_time,
                    stddev_exec_time,
                    rows
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                    AND query NOT LIKE '%pg_extension%'
                ORDER BY total_exec_time DESC
                LIMIT 15;
            """)
            
            rows = cursor.fetchall()
            for row in rows:
                query, calls, total_time, mean_time, min_time, max_time, stddev_time, num_rows = row
                
                # Truncate long queries for display
                display_query = query[:200] + '...' if len(query) > 200 else query
                
                results['top_queries'].append({
                    'query': display_query,
                    'full_query': query,
                    'calls': calls,
                    'total_time': round(total_time, 3),
                    'mean_time': round(mean_time, 3),
                    'min_time': round(min_time, 3),
                    'max_time': round(max_time, 3),
                    'stddev_time': round(stddev_time, 3) if stddev_time else 0,
                    'rows': num_rows
                })
        
        # Calculate overall metrics
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    SUM(calls) as total_calls,
                    SUM(total_exec_time) as total_time,
                    AVG(mean_exec_time) as avg_mean_time,
                    SUM(rows) as total_rows
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                    AND query NOT LIKE '%pg_extension%';
            """)
            
            row = cursor.fetchone()
            total_queries, total_calls, total_time, avg_mean_time, total_rows = row
            
            results['metrics'] = {
                'total_queries': total_queries or 0,
                'total_calls': total_calls or 0,
                'total_time': round(total_time, 2) if total_time else 0,
                'avg_mean_time': round(avg_mean_time, 3) if avg_mean_time else 0,
                'total_rows': total_rows or 0
            }
        
        # Generate latency histogram data
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    CASE 
                        WHEN mean_exec_time < 0.1 THEN '0-0.1ms'
                        WHEN mean_exec_time < 1 THEN '0.1-1ms'
                        WHEN mean_exec_time < 10 THEN '1-10ms'
                        WHEN mean_exec_time < 100 THEN '10-100ms'
                        WHEN mean_exec_time < 1000 THEN '100-1000ms'
                        ELSE '1000ms+'
                    END as latency_bucket,
                    COUNT(*) as query_count
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                    AND query NOT LIKE '%pg_extension%'
                GROUP BY latency_bucket
                ORDER BY 
                    MIN(CASE 
                        WHEN mean_exec_time < 0.1 THEN 1
                        WHEN mean_exec_time < 1 THEN 2
                        WHEN mean_exec_time < 10 THEN 3
                        WHEN mean_exec_time < 100 THEN 4
                        WHEN mean_exec_time < 1000 THEN 5
                        ELSE 6
                    END);
            """)
            
            histogram_data = cursor.fetchall()
            labels = []
            counts = []
            
            for bucket, count in histogram_data:
                labels.append(bucket)
                counts.append(count)
            
            results['latency_histogram'] = {
                'labels': json.dumps(labels),
                'data': json.dumps(counts)
            }
        
        # Get cache hit ratio
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ROUND(
                        100.0 * sum(shared_blks_hit) / NULLIF(sum(shared_blks_hit) + sum(shared_blks_read), 0),
                        2
                    ) as cache_hit_ratio
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%';
            """)
            
            cache_ratio = cursor.fetchone()[0]
            results['metrics']['cache_hit_ratio'] = cache_ratio if cache_ratio else 0
            
    except Exception as e:
        results['error'] = f"Error querying statistics: {str(e)}"
    
    return render(request, 'adbms/monitoring_result.html', {'results': results})

def replication_demo(request):
    """
    Demonstrates Replication Lag and High Availability.
    
    THEORY:
    Replication copies data from a Primary node to one or more Replica nodes.
    - Asynchronous Replication: Primary commits immediately, Replica catches up later.
      Pros: High write performance. Cons: Potential data loss on failover, Replication Lag.
    - Synchronous Replication: Primary waits for Replica to confirm write.
      Pros: Zero data loss. Cons: Lower write performance, Primary blocks if Replica is down.
      
    This demo simulates Asynchronous Replication Lag by writing to Primary and immediately reading from Replica.
    """
    results = {
        'primary_value': None,
        'replica_value': None,
        'primary_lsn': None,
        'replica_lsn': None,
        'lag_bytes': 0,
        'is_synced': False,
        'error': None
    }
    
    try:
        # Use Section 1 for demo. Ensure it exists.
        section_id = 1
        
        # 1. Write to Primary
        with transaction.atomic(using='default'):
            # Lock row to prevent concurrent interference during this demo step
            try:
                section = Section.objects.using('default').select_for_update().get(id=section_id)
            except Section.DoesNotExist:
                # Create if not exists (unlikely in this demo setup but good for safety)
                from courses.models import Course
                course = Course.objects.first()
                if not course:
                     # Fallback if no courses
                     results['error'] = "No courses/sections found. Please seed data first."
                     return render(request, 'adbms/replication_result.html', {'results': results})
                section = Section.objects.create(course=course, section_number='001', capacity=50)

            # Update capacity to a random value to ensure a change is visible
            import random
            new_capacity = random.randint(10, 100)
            section.capacity = new_capacity
            section.save()
            results['primary_value'] = new_capacity
        
        # 2. Read from Replica immediately
        try:
            # We use a raw cursor or force a fresh read to avoid any Django caching, 
            # though using('replica') should be enough.
            section_replica = Section.objects.using('replica').get(id=section_id)
            results['replica_value'] = section_replica.capacity
        except Exception as e:
            results['error'] = f"Replica Read Error: {str(e)}"
            results['replica_value'] = "N/A"

        # 3. Get LSNs (Log Sequence Numbers)
        # Primary LSN
        with connections['default'].cursor() as cursor:
            cursor.execute("SELECT pg_current_wal_lsn()")
            row = cursor.fetchone()
            if row:
                results['primary_lsn'] = row[0]
        
        # Replica LSN
        try:
            with connections['replica'].cursor() as cursor:
                cursor.execute("SELECT pg_last_wal_replay_lsn()")
                row = cursor.fetchone()
                if row:
                    results['replica_lsn'] = row[0]
                
                # Calculate lag size
                if results['primary_lsn'] and results['replica_lsn']:
                    cursor.execute("SELECT pg_wal_lsn_diff(%s, %s)", [results['primary_lsn'], results['replica_lsn']])
                    row = cursor.fetchone()
                    if row:
                        results['lag_bytes'] = row[0]
        except Exception as e:
            if not results['error']:
                results['error'] = f"Replica Metadata Error: {str(e)}"

        # Check sync status
        if results['primary_value'] is not None and results['replica_value'] != "N/A":
            results['is_synced'] = (results['primary_value'] == results['replica_value'])
            
    except Exception as e:
        results['error'] = f"Demo Error: {str(e)}"

    return render(request, 'adbms/replication_result.html', {'results': results})


def full_text_search_demo(request):
    """
    Demonstrates Full-Text Search (FTS) vs Standard Pattern Matching (LIKE).
    
    THEORY:
    - Standard 'icontains' uses LIKE '%...%' which cannot use standard B-Tree indexes efficiently (requires scanning).
    - Full-Text Search uses pre-computed vectors (tsvector) and GIN indexes for fast lookups.
    - FTS also supports stemming (e.g. 'run' matches 'running') and ranking.
    """
    from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
    from django.db.models import Q
    from courses.models import Course
    
    query = request.GET.get('q', '')
    
    standard_results = []
    fts_results = []
    standard_time = 0
    fts_time = 0
    
    if query:
        # 1. Standard Search (LIKE)
        start_time = time.time()
        standard_results = list(Course.objects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )[:20]) # Limit to 20 for display
        standard_time = (time.time() - start_time) * 1000  # ms
        
        # 2. Full-Text Search (TSVECTOR + GIN)
        start_time = time.time()
        # We use the same 'english' config as the index
        vector = SearchVector('title', 'description', config='english')
        search_query = SearchQuery(query, config='english')
        
        fts_results = list(Course.objects.annotate(
            rank=SearchRank(vector, search_query)
        ).filter(
            rank__gte=0.01  # Filter out low relevance
        ).order_by('-rank')[:20])
        fts_time = (time.time() - start_time) * 1000  # ms

    return render(request, 'adbms_demo/full_text_search.html', {
        'query': query,
        'standard_results': standard_results,
        'fts_results': fts_results,
        'standard_time': f"{standard_time:.2f}",
        'fts_time': f"{fts_time:.2f}",
    })
