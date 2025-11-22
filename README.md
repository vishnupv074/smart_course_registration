# Smart Course Registration System

A Django-based Course Registration System designed to demonstrate Advanced DBMS concepts such as ACID transactions, isolation levels, concurrency control, and query optimization using PostgreSQL.

## Features

-   **User Management**: Student, Instructor, and Admin roles.
-   **Course Management**: Create and manage courses and sections.
-   **Enrollment System**: ACID-compliant enrollment with capacity checks and concurrency control.
-   **ADBMS Demos**: Visualizations and simulations for isolation anomalies, locking, and performance tuning (In Progress).

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
5.  **Access the App**:
    -   Web: [http://localhost:8000/](http://localhost:8000/)
    -   API Docs: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)

## Documentation

Detailed documentation is available in the `docs/` directory:
-   [Setup Guide](docs/setup_guide.md)
-   [Project Structure](docs/project_structure.md)