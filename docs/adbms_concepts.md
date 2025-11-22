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

---

## 3. Deadlock (Planned)

### Concept
A **Deadlock** occurs when two transactions are waiting for each other to give up locks.

### Simulation Strategy
-   **Transaction A**: Locks Row 1. Sleeps. Tries to Lock Row 2.
-   **Transaction B**: Locks Row 2. Sleeps. Tries to Lock Row 1.
-   **Result**: Database detects deadlock and aborts one transaction.

### Mitigation
-   **Ordering Updates**: Always acquire locks in a consistent order (e.g., sort by ID).
-   **Timeouts**: Set `lock_timeout` to fail fast.
