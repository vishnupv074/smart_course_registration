# Smart Course Registration System

A Django-based Course Registration System designed to demonstrate Advanced DBMS concepts such as ACID transactions, isolation levels, concurrency control, and query optimization using PostgreSQL.

## Features

### Core Functionality
-   **User Management**: Role-based access for Students, Instructors, and Admins.
-   **User Profiles**: Comprehensive profile system with:
    -   Profile picture uploads
    -   Personal information (DOB, address, location)
    -   Social media links (LinkedIn, GitHub, Twitter)
    -   Password change functionality
    -   Email verification system
-   **Course Catalog**: Searchable and paginated list of courses and sections.
-   **Instructor Dashboard**: Manage courses, sections, and view enrolled students.
-   **Student Dashboard**: View enrollments, browse courses, and drop courses.
-   **Enrollment System**:
    -   **ACID Compliance**: Atomic enrollment transactions with capacity checks.
    -   **Conflict Detection**: Prevents scheduling conflicts.
    -   **Concurrency Control**: Pessimistic locking to prevent race conditions.

### ADBMS Demonstrations
Interactive tools to visualize advanced database concepts:
-   **Isolation Levels**: Simulate anomalies like Non-Repeatable Reads and Phantom Reads.
-   **Concurrency & Locking**: Visualize Row Locking and Deadlock scenarios.
-   **Indexing**: Benchmark performance of B-Tree indexes vs Sequential Scans.
-   **Query Optimization**: Visualizer for `EXPLAIN ANALYZE` to analyze query costs and execution plans.
-   **Table Partitioning**: Benchmark performance of Partitioned vs Non-Partitioned tables (Partition Pruning).

## Quick Start

1.  **Clone the repository**.
2.  **Copy the sample environment file**:
    ```bash
    cp .env.sample .env
    ```
3.  **Run with Docker Compose**:
    ```bash
    docker-compose up -d --build
    ```
4.  **Apply Migrations**:
    ```bash
    docker-compose exec web python manage.py migrate
    ```
5.  **Create Superuser**:
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```
6.  **Access the App**:
    -   Web: [http://localhost:8000/](http://localhost:8000/)
    -   API Docs: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

## Documentation

Detailed documentation is available in the `docs/` directory:
-   [Setup Guide](docs/setup_guide.md)
-   [ADBMS Concepts](docs/adbms_concepts.md)