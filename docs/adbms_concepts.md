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

2.  **Transaction B** (Celery Task):
    -   Wait 1 second (to ensure A has started).
    -   Updates the Section capacity to **100**.
    -   Commits.

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
    -   Transaction A counts enrollments, sleeps, then counts again.
    -   Transaction B (Celery) inserts a new enrollment for a "phantom_user" during the sleep.
    -   Result: The second count is higher than the first, demonstrating the phantom read.

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

### Mitigation
-   **Ordering Updates**: Always acquire locks in a consistent order (e.g., sort by ID).
-   **Timeouts**: Set `lock_timeout` to fail fast.

---

## 4. Indexing & Performance

### Concept
Indexes are data structures that improve the speed of data retrieval operations on a database table at the cost of additional writes and storage space.

### Demo in Application
-   **URL**: `http://localhost:8000/adbms/indexing/`
-   **Setup**: We seeded the database with 100,000 course records.
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

### Conclusion
Indexing provides massive performance gains for lookup queries on large datasets. However, indexes should be chosen carefully as they slow down `INSERT`, `UPDATE`, and `DELETE` operations.

