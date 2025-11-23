# Smart Course Registration System - Implementation History & Roadmap

**Last Updated:** November 23, 2025

## 1. Abstract
The Smart Course Registration System is designed to demonstrate the practical application of Advanced Database Management System (ADBM) principles through a real-world academic use case. The system provides a platform for students to register for courses, manage enrollments, and track seat availability, ensuring efficient and consistent data handling.

The project emphasizes database integrity, transaction management, and concurrency control, implementing essential ADBMS concepts such as ACID properties, isolation levels, indexing, and query optimization. It ensures data consistency even under concurrent access, showcasing how theoretical database concepts translate into reliable, high-performance applications.

Additionally, the system includes mechanisms for data logging, performance analysis, and query efficiency evaluation, enabling users to observe how different database optimization strategies affect system performance. This project highlights the importance of optimized database design, integrity constraints, and controlled concurrency in building scalable and robust academic management systems.

## 2. Core Concepts & Requirements
The following concepts are central to the project's implementation:

### Core Functionalities
*   **User Management:** Student registration, authentication, and role-based access for students, instructors, and administrators.
*   **Course and Section Management:** Creation, update, and management of courses, sections, and seat capacities.
*   **Enrollment and Transaction Control:** Atomic enrollment operations ensuring ACID compliance and concurrency safety.
*   **Query Optimization:** Implementation of indexing and query plan evaluation for performance improvement.
*   **Data Integrity and Triggers:** Use of constraints and triggers to maintain valid enrollment data.
*   **Performance Monitoring:** Logging and analysis of database operations for optimization insights.
*   **Admin Dashboard:** Visualization of course popularity, enrollment statistics, and system performance metrics.

### ADBMS Concepts to Cover
*   **ACID & Transactions:** commit/rollback, nested transactions, transaction.atomic, manual control.
*   **Isolation levels & concurrency control:** READ UNCOMMITTED/COMMITTED/REPEATABLE READ/SERIALIZABLE simulation and visualization of anomalies (phantom, non-repeatable reads, lost updates, dirty reads).
*   **Concurrency & locking:** row/table locks, deadlock simulation and resolution.
*   **Indexing:** B-tree, partial, expression, unique, multi-column; compare performance.
*   **Query optimization & plans:** EXPLAIN/EXPLAIN ANALYZE, plan visualizer, cost vs actual rows.
*   **Normalization & denormalization:** normalized schema vs denormalized materialized view for analytics.
*   **Materialized views & refresh strategies:** incremental refresh vs full refresh.
*   **Partitioning:** range or list partitioning (Postgres), and performance impact.
*   **Triggers & stored procedures:** trigger-based audit logs and constraints in DB (PL/pgSQL).
*   **MVCC & visibility:** demonstrate versioning effects (Postgres MVCC).
*   **Replication / HA:** read replica setup (or simulated) and consistency tradeoffs.
*   **Backup & restore:** show pg_dump/pg_restore in Docker demo.
*   **Monitoring & statistics:** pg_stat_statements, explain plan collection, histogram of latencies.
*   **Full-text search, transactions with message queues:** using Postgres full-text or Elasticsearch; Celery for async tasks.
*   **Benchmarking & workload generation:** script to replay realistic workloads and measure TPS/latency.

## 3. Tech Stack
- **Backend:** Django 5.x, Django REST Framework
- **Database:** PostgreSQL 16 (running in Docker)
- **Async Tasks:** Celery + Redis
- **Frontend:** Django Templates + Bootstrap 5
- **Infrastructure:** Docker Compose

## 4. Implemented Features

### A. Core Registration System
1.  **User Roles:**
    *   **Student:** Browse courses, enroll, drop courses, view schedule.
    *   **Instructor:** Manage courses/sections, view enrolled students.
    *   **Admin:** System management.
2.  **Course & Section Management:**
    *   Instructors can create/edit courses and sections.
    *   Sections have capacity limits and schedules.
3.  **Enrollment Logic:**
    *   **Capacity Check:** Prevents enrolling if section is full.
    *   **Conflict Detection:** Prevents enrolling in overlapping schedules.
    *   **ACID Transactions:** Enrollment and dropping are atomic operations.
    *   **Pessimistic Locking:** Uses `select_for_update()` to prevent race conditions during enrollment.

### B. ADBMS Demonstrations
These features are located in the `adbms_demo` app and accessible via the **ADBMS Dashboard**.

#### 1. Transaction Isolation & Concurrency
*   **Non-Repeatable Read:** Demonstrates how reading the same row twice in a transaction yields different results if another transaction commits a change in between.
*   **Phantom Read:** Demonstrates how a range query result changes if another transaction inserts a new row matching the criteria.
*   **Deadlock Simulation:** Intentionally creates a deadlock between two tasks (Task A locks Res 1 then wants Res 2; Task B locks Res 2 then wants Res 1) to show how PostgreSQL detects and kills one transaction.
*   **Row Locking (SELECT FOR UPDATE):**
    *   **Goal:** Prevent double-booking.
    *   **Implementation:** Transaction A locks a section row. Transaction B attempts to book the same section but is forced to wait until A completes.
    *   **Status:** Implemented in `row_locking_demo` view and `attempt_booking_task`.

#### 2. Performance & Optimization
*   **Indexing Benchmark:**
    *   Compares query performance (Execution Time) between a non-indexed column search and an indexed column search.
    *   Uses `EXPLAIN ANALYZE`.
*   **Query Optimization Visualizer:**
    *   Allows users to input raw SQL.
    *   Visualizes the Query Plan, Cost, and Execution Time.
*   **Table Partitioning:**
    *   **Goal:** Demonstrate performance improvement for large datasets using Partition Pruning.
    *   **Implementation:**
        *   `NonPartitionedEnrollment`: Standard table.
        *   `PartitionedEnrollment`: Table partitioned by `LIST (semester)` (Fall 2024, Spring 2025, etc.).
        *   **Demo:** Populates 20k+ rows and compares `SELECT * WHERE semester='Fall 2024'` on both tables.
        *   **Status:** Models created, Custom SQL Migration applied, View `partitioning_demo` implemented.

## 5. Code Structure Key Points

### Database Models
*   `users.User`: Custom user model with roles.
*   `courses.Course`, `courses.Section`: Core academic data.
*   `enrollment.Enrollment`: Links Students to Sections.
*   `adbms_demo.NonPartitionedEnrollment`, `adbms_demo.PartitionedEnrollment`: Dedicated models for the partitioning demo (managed via custom migrations).

### Key Views & Tasks
*   `adbms_demo/views.py`: Contains the logic for all ADBMS simulations.
*   `adbms_demo/tasks.py`: Contains Celery tasks for background simulations (Deadlocks, Concurrent Booking attempts).
*   `enrollment/views.py`: Contains the production-grade enrollment logic with `transaction.atomic()` and `select_for_update()`.

## 6. Recent Changes (Session Context)
*   **Partitioning:** Added `PartitionedEnrollment` model and custom SQL migration to create partitions. Implemented `partitioning_demo` view to benchmark pruning.
*   **Row Locking:** Implemented `row_locking_demo` to visualize `SELECT FOR UPDATE` blocking behavior.
*   **User Profile:** Fully implemented comprehensive profile system with:
    *   Profile picture uploads (avatar field with ImageField)
    *   Additional personal fields (DOB, address, city, country)
    *   Social media integration (LinkedIn, GitHub, Twitter)
    *   Password change functionality
    *   Email verification system with token-based verification
*   **Documentation:** Updated `README.md`, `walkthrough.md`, and `adbms_concepts.md`.
*   **Verification:** Verified Partitioning Demo with performance benchmarks (1.78ms vs 0.75ms).

## 7. Pending / Next Steps

### Immediate Tasks
*   **[DONE] Verify Partitioning Demo:** Verified that the demo works as expected and shows performance gains (Partition Pruning).
*   **[DONE] User Profile:** Fully implemented with profile pictures, additional fields, social media links, password change, and email verification.

### Enhanced Course Registration Features
*   **Admin Dashboard:** Implement a comprehensive dashboard with:
    *   **Analytics:** Enrollment trends, popular courses, seat utilization rates.
    *   **Stats:** Total students, active instructors, daily registrations.
    *   **System Health:** Database connection status, task queue depth.
*   **UI/UX Improvements:** Modernize the interface with better styling, interactive elements, and responsive design.
*   **Advanced Functionality:** Waitlist management, course prerequisites, and bulk operations.

### Remaining ADBMS Concepts
*   **Normalization vs Denormalization:** Implement materialized views for analytics (e.g., "Average GPA per Course").
*   **Triggers & Stored Procedures:** Implement PL/pgSQL triggers for audit logs (e.g., logging grade changes).
*   **MVCC & Visibility:** Demonstrate Postgres versioning and visibility rules.
*   **Replication / HA:** Simulate read replica setup and consistency tradeoffs.
*   **Backup & Restore:** Demonstrate `pg_dump` and `pg_restore` workflows.
*   **Monitoring & Statistics:** Visualize `pg_stat_statements` and query latency histograms.
*   **Full-text Search:** Implement search using Postgres Full-Text Search or Elasticsearch.
*   **Benchmarking:** Create scripts to replay realistic workloads and measure TPS/latency.
