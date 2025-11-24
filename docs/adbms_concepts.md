# Advanced DBMS Concepts

This document explains the advanced database concepts demonstrated in the Smart Course Registration System.

## 1. Transaction Isolation Levels

### Concept
Isolation levels define the degree to which a transaction must be isolated from the data modifications made by other transactions.

### Anomalies Demonstrated
- **Non-Repeatable Read**: A transaction reads the same row twice and gets different data because another transaction updated it in between.
- **Phantom Read**: A transaction executes a query returning a set of rows that satisfy a search condition and finds that the set of rows satisfying the condition has changed due to another recently-committed transaction.

### Implementation
We use `SET TRANSACTION ISOLATION LEVEL` in Django views to simulate these anomalies.

---

## 2. Concurrency Control & Locking

### Concept
Concurrency control ensures that correct results for concurrent operations are generated, while getting those results as quickly as possible.

### Techniques Demonstrated
- **Pessimistic Locking (`SELECT FOR UPDATE`)**: Prevents race conditions (like double booking) by locking rows until the transaction completes.
- **Deadlock Detection**: Demonstrates how the database detects circular wait conditions and resolves them by aborting one transaction.

---

## 3. Query Optimization & Indexing

### Concept
Indexing improves the speed of data retrieval operations on a database table at the cost of additional writes and storage space.

### Demonstrations
- **Indexing Benchmark**: Compares execution time of queries with and without B-Tree indexes.
- **Query Plan Visualization**: Uses `EXPLAIN ANALYZE` to show how the database executes a query (Sequential Scan vs Index Scan).

---

## 4. Table Partitioning

### Concept
Partitioning splits a large table into smaller, more manageable pieces, while still allowing them to be accessed as a single table.

### Benefits
- **Partition Pruning**: The query planner can skip scanning partitions that cannot contain matching rows.
- **Maintenance**: Easier to manage large datasets (e.g., dropping old data).

### Implementation
We use **List Partitioning** by semester. Queries filtering by semester only scan the relevant partition.

---

## 5. Triggers & Stored Procedures (PL/pgSQL)

### Concept
A **Database Trigger** is procedural code that is automatically executed in response to certain events on a particular table or view in a database.

### Implementation: Audit Logging
We implemented a comprehensive audit logging system using **AFTER INSERT/UPDATE/DELETE** triggers on 4 critical tables:
1.  `Enrollment`
2.  `Course`
3.  `Section`
4.  `Waitlist`

### PL/pgSQL Function Structure
Each table has a dedicated PL/pgSQL function (e.g., `audit_enrollment_changes()`) that:
1.  Checks the operation type (`TG_OP`).
2.  Captures `OLD` (before) and `NEW` (after) row data as JSON.
3.  Generates a human-readable change summary.
4.  Inserts a record into the `AuditLog` table.

```sql
CREATE OR REPLACE FUNCTION audit_enrollment_changes()
RETURNS TRIGGER AS $$
BEGIN
    -- Logic to capture changes
    INSERT INTO adbms_demo_auditlog (...) VALUES (...);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Database vs Application Auditing

| Feature | Database Triggers (PL/pgSQL) | Application Logic (Django Signals) |
| :--- | :--- | :--- |
| **Reliability** | **High**: Captures ALL changes (SQL, Admin, App) | **Medium**: Misses direct SQL/bulk updates |
| **Performance** | **High**: Runs inside DB, no network overhead | **Medium**: Python overhead, extra DB roundtrips |
| **Maintenance** | **Medium**: Requires SQL/PLpgSQL knowledge | **High**: Easier (Python code) |
| **Complexity** | **Medium**: Logic split between App and DB | **Low**: Logic centralized in App |
| **Coupling** | **Loose**: App doesn't need to know about auditing | **Tight**: App must explicitly trigger audit |

### When to use Triggers?
- **Audit Logging**: When you need a guaranteed audit trail for compliance.
- **Data Integrity**: Enforcing complex constraints across tables.
- **Denormalization**: Automatically updating summary tables (e.g., incrementing a counter).

---

## 6. Normalization vs Denormalization

### Concept
**Normalization** organizes data to reduce redundancy and improve integrity, while **Denormalization** adds redundancy to improve read performance by reducing or eliminating joins.

### The Tradeoff

| Aspect | Normalized | Denormalized |
| :--- | :--- | :--- |
| **Storage** | Minimal (no redundancy) | Higher (duplicate data) |
| **Read Performance** | Slower (requires joins) | Faster (no joins needed) |
| **Write Performance** | Faster (single location) | Slower (multiple locations) |
| **Data Integrity** | High (single source of truth) | Risk of inconsistency |
| **Maintenance** | Easier updates | Requires refresh strategy |
| **Use Case** | OLTP (transactions) | OLAP (analytics) |

### Implementation: Materialized Views

We use **PostgreSQL Materialized Views** to demonstrate denormalization:

```sql
CREATE MATERIALIZED VIEW adbms_demo_materialized_enrollment AS
SELECT
    row_number() OVER () AS id,
    u.username as student_name,
    c.code as course_code,
    c.title as course_title,
    s.semester as semester,
    e.grade as grade,
    c.credits as credits
FROM enrollment_enrollment e
JOIN users_user u ON e.student_id = u.id
JOIN courses_section s ON e.section_id = s.id
JOIN courses_course c ON s.course_id = c.id;
```

### Performance Results

| Approach | Execution Time | Operations | Improvement |
| :--- | :--- | :--- | :--- |
| **Normalized** | ~0.275ms | 3 JOINs + filtering | Baseline |
| **Denormalized** | ~0.02ms | Simple table scan | **13.75x faster** |

### Key Benefits
- **Pre-computed Joins**: Data already combined and stored physically
- **Sequential Reads**: All related data stored together
- **Reduced I/O**: Fewer disk seeks and page reads
- **Simpler Query Plans**: No complex join operations

### Refresh Strategies
```sql
-- Manual refresh
REFRESH MATERIALIZED VIEW adbms_demo_materialized_enrollment;

-- Concurrent refresh (non-blocking)
REFRESH MATERIALIZED VIEW CONCURRENTLY adbms_demo_materialized_enrollment;
```

### When to Use Materialized Views?
- Analytics and reporting queries
- Read-heavy workloads
- Complex aggregations
- Data that changes infrequently
- When you can tolerate slightly stale data

For detailed explanation, see [Normalization vs Denormalization Guide](normalization_vs_denormalization.md).
