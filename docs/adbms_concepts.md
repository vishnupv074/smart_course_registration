# ADBMS Concepts in Smart Course Registration System

This document details the Advanced Database Management System (ADBMS) concepts demonstrated in this project, explaining the theory, simulation, and mitigation strategies.

## 1. Non-Repeatable Read

### Concept
A **Non-Repeatable Read** occurs when a transaction reads the same row twice but gets different data each time. This happens because another concurrent transaction modified and committed the data between the two reads.

**Isolation Level**: Occurs in `READ COMMITTED` (Default in PostgreSQL).
**Prevented by**: `REPEATABLE READ` or `SERIALIZABLE`.

### Impact
In a course registration system, this could lead to inconsistent decisions. For example, a student checks seat availability (reads 5 seats), starts filling the form, and submits. If another student took the last seat in the meantime, the first student might still think there are seats available if the system checks again and sees inconsistent data (though in this specific case, it's more of a race condition usually solved by locking).

### Demo in Application

-   **URL**: `http://localhost:8000/adbms/non-repeatable-read/`
-   **How to Run**:
    1.  Navigate to the URL or click "Explore Demos" -> "Non-Repeatable Read".
    2.  The system runs the simulation automatically.
    3.  View the "Execution Log" to see the sequence of events and the detected anomaly.

### Technical Simulation
We simulate this using a Django View (`Transaction A`) and a Celery Task (`Transaction B`).

1.  **Transaction A** (View):
    -   Starts a transaction (`atomic`).
    -   Reads the Section capacity (**Value: 50**).
    -   Triggers the Celery task.
    -   Sleeps for 3 seconds to allow the task to finish.
    -   Reads the Section capacity again.
    -   **Result**: Sees **Value: 100**. The value changed within the same transaction!

    -   Updates the Section capacity to **100**.
    -   Commits.

### Technical Implementation
The simulation uses `transaction.atomic()` to manage the transaction scope and `time.sleep()` to orchestrate the race condition.

**Code Snippet (`adbms_demo/views.py`):**
```python
with transaction.atomic():
    # Step 1: First Read
    s1 = Section.objects.get(id=section.id)
    
    # Step 2: Trigger Transaction B (Background Task)
    update_section_capacity.delay(section.id, new_capacity=100, delay=1)
    
    # Sleep to allow Transaction B to complete
    time.sleep(3)

    # Step 3: Second Read
    # In READ COMMITTED, this sees the new value (100)
    s2 = Section.objects.get(id=section.id)
```

### Mitigation in Application
In the actual **Enrollment System** (`enrollment/views.py`), we mitigate this and other concurrency issues using **Pessimistic Locking**.

```python
with transaction.atomic():
    # select_for_update() locks the row until the transaction ends.
    # No other transaction can modify this row while we hold the lock.
    section = Section.objects.select_for_update().get(id=section_id)
    
    # ... perform checks and enrollment ...
```

By using `select_for_update()`, we ensure that once we read the section capacity, no one else can change it until we are done enrolling. This effectively serializes access to that specific course section.

---

## 2. Phantom Read (Planned)

### Concept
A **Phantom Read** occurs when a transaction executes a query returning a set of rows that satisfy a search condition, but a concurrent transaction inserts a new row that matches the condition. If the first transaction repeats the query, it sees the "phantom" row.

### Simulation Strategy
-   **Transaction A**: `SELECT count(*) FROM enrollments WHERE section_id=1`.
-   **Transaction B**: `INSERT INTO enrollments ...` (for section 1).
-   **Transaction A**: `SELECT count(*) ...` -> Returns a different count.

### Demo in Application
-   **URL**: `http://localhost:8000/adbms/phantom-read/`
-   **Technical Details**:
    -   Transaction B (Celery) inserts a new enrollment for a "phantom_user" during the sleep.
    -   Result: The second count is higher than the first, demonstrating the phantom read.

### Technical Implementation
Similar to Non-Repeatable Read, this uses a background task to insert data while the main transaction is active.

**Code Snippet (`adbms_demo/views.py`):**
```python
with transaction.atomic():
    # Step 1: First Count
    count1 = Enrollment.objects.filter(section=section).count()

    # Step 2: Trigger Transaction B
    insert_enrollment.delay(section.id, delay=1)

    # Sleep to allow Transaction B to complete
    time.sleep(3)

    # Step 3: Second Count
    count2 = Enrollment.objects.filter(section=section).count()
```

---

## 3. Deadlock

### Concept
A **Deadlock** occurs when two transactions are waiting for each other to give up locks.

### Simulation Strategy
-   **Transaction A**: Locks Row 1. Sleeps. Tries to Lock Row 2.
-   **Transaction B**: Locks Row 2. Sleeps. Tries to Lock Row 1.
-   **Result**: Database detects deadlock and aborts one transaction.

### Demo in Application
-   **URL**: `http://localhost:8000/adbms/deadlock/`
-   **Technical Details**:
    -   Two Celery tasks are triggered simultaneously.
    -   Task A locks Section 1, waits, then tries to lock Section 2.
    -   Task B locks Section 2, waits, then tries to lock Section 1.
    -   PostgreSQL's deadlock detector identifies the cycle and terminates one of the transactions (usually the one that detected the deadlock).
    -   Check Celery logs (`docker-compose logs -f celery`) to see the `DeadlockDetected` error.

### Technical Implementation
We define two Celery tasks that attempt to acquire `select_for_update()` locks in opposing orders.

**Code Snippet (`adbms_demo/tasks.py`):**
```python
# Task A
with transaction.atomic():
    Section.objects.select_for_update().get(id=section_id_1)
    time.sleep(2)
    Section.objects.select_for_update().get(id=section_id_2)

# Task B
with transaction.atomic():
    Section.objects.select_for_update().get(id=section_id_2)
    time.sleep(2)
    Section.objects.select_for_update().get(id=section_id_1)
```

### Mitigation
-   **Ordering Updates**: Always acquire locks in a consistent order (e.g., sort by ID).
-   **Timeouts**: Set `lock_timeout` to fail fast.

---

## 4. Indexing & Performance

### Concept
Indexes are data structures that improve the speed of data retrieval operations on a database table at the cost of additional writes and storage space.

### Demo in Application
-   **URL**: `http://localhost:8000/adbms/indexing/`
-   **Setup**: We seeded the database with 100,000 course records using the custom management command:
    ```bash
    docker-compose exec web python manage.py seed_data --courses 100000
    ```
-   **Benchmark**: We compare two queries using `EXPLAIN ANALYZE`.

### Scenarios

#### 1. No Index (Sequential Scan)
-   **Query**: `SELECT * FROM courses_course WHERE description LIKE '%Description%'`
-   **Mechanism**: The database must scan every single row in the table (Sequential Scan) to find matches because there is no index on the `description` column.
-   **Performance**: Slow (e.g., ~15-30ms+ depending on hardware). O(N) complexity.

#### 2. B-Tree Index (Index Scan)
-   **Query**: `SELECT * FROM courses_course WHERE code = 'CS050000'`
-   **Mechanism**: The database uses the B-Tree index on the `code` column (created by the `unique=True` constraint) to jump directly to the target row.
-   **Performance**: Extremely fast (e.g., < 0.1ms). O(log N) complexity.

### Technical Implementation
The application uses PostgreSQL's `EXPLAIN (ANALYZE, FORMAT JSON)` command to execute these queries and capture the actual execution time and plan node type.

**Code Snippet (`adbms_demo/views.py`):**
```python
with connection.cursor() as cursor:
    # Execute EXPLAIN ANALYZE to get performance metrics
    cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query, [param])
    explain_output = cursor.fetchone()[0][0]
    
    # Extract key metrics
    execution_time = explain_output['Execution Time']
    plan_node = explain_output['Plan']['Node Type']
```

The results are then parsed and displayed on the dashboard, showing the stark contrast between `Seq Scan` (scanning all 100k rows) and `Index Scan` (using the B-Tree structure).

### Conclusion
Indexing provides massive performance gains for lookup queries on large datasets. However, indexes should be chosen carefully as they slow down `INSERT`, `UPDATE`, and `DELETE` operations.


---

## 5. Query Optimization Visualizer

### Concept
Query Optimization is the process of selecting the most efficient execution plan for a SQL query. The database optimizer considers various factors like table size, available indexes, and join algorithms.

### Demo in Application
-   **URL**: `http://localhost:8000/adbms/query-optimization/`
-   **Features**:
    -   **Interactive Input**: Users can input custom SQL queries.
    -   **Visual Feedback**: Displays Execution Time, Total Cost, and the Query Plan (e.g., `Seq Scan`, `Index Scan`, `Hash Join`).
    -   **Presets**: Pre-loaded queries to demonstrate specific optimization scenarios.

### Technical Implementation
The tool accepts a raw SQL query, validates it (restricting to `SELECT` for safety), and wraps it in `EXPLAIN (ANALYZE, FORMAT JSON)`. The JSON output is parsed to extract key performance metrics.

**Code Snippet (`adbms_demo/views.py`):**
```python
cursor.execute(f"EXPLAIN (ANALYZE, FORMAT JSON) {query}")
explain_output = cursor.fetchone()[0][0]
results = {
    'execution_time': explain_output['Execution Time'],
    'total_cost': explain_output['Plan']['Total Cost'],
    'plan_node': explain_output['Plan']['Node Type']
}
```

---

## 6. Table Partitioning

### Concept
**Table Partitioning** is a database design technique where a large table is split into smaller, more manageable pieces called partitions. PostgreSQL supports partitioning by Range, List, or Hash.

**Benefit**: **Partition Pruning**. When a query filters by the partition key, the query planner can skip scanning irrelevant partitions entirely, significantly reducing I/O and execution time.

### Demo in Application
-   **URL**: `http://localhost:8000/adbms/partitioning/`
-   **Setup**:
    -   **Non-Partitioned Table**: `adbms_demo_nonpartitionedenrollment` (Standard table).
    -   **Partitioned Table**: `adbms_demo_partitionedenrollment` (Partitioned by `LIST (semester)`).
    -   **Data**: Both tables are populated with ~20,000 rows of dummy enrollment data.

### Scenarios

#### 1. Non-Partitioned Query
-   **Query**: `SELECT * FROM non_partitioned WHERE semester = 'Fall 2024'`
-   **Plan**: `Seq Scan` on the entire table.
-   **Result**: Slower execution as it scans all rows (including Spring 2025, Fall 2025, etc.).

#### 2. Partitioned Query
-   **Query**: `SELECT * FROM partitioned WHERE semester = 'Fall 2024'`
-   **Plan**: `Seq Scan` on `adbms_demo_partitionedenrollment_fall2024` ONLY.
-   **Result**: Faster execution due to pruning.

### Technical Implementation
We used a **Custom SQL Migration** to create the partitioned table since Django's ORM does not natively support creating partitioned tables (though it can query them).

**Migration Snippet:**
```sql
CREATE TABLE adbms_demo_partitionedenrollment (
    id SERIAL,
    ...
    semester VARCHAR(20) NOT NULL
) PARTITION BY LIST (semester);

CREATE TABLE adbms_demo_partitionedenrollment_fall2024 
    PARTITION OF adbms_demo_partitionedenrollment 
    FOR VALUES IN ('Fall 2024');
```

**Code Snippet (`adbms_demo/views.py`):**
```python
# We run EXPLAIN ANALYZE on both queries to compare performance
cursor.execute("EXPLAIN (ANALYZE, FORMAT JSON) " + query_part, [target_semester])
```
