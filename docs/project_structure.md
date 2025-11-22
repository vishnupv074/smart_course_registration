# Smart Course Registration System - Project Structure & Architecture

This document outlines the low-level details of the project structure, database schema, and key components implemented so far.

## Project Structure

```text
smart_course_registration/
├── config/                 # Project configuration (settings, urls, wsgi)
│   ├── settings.py         # Django settings (Env vars, Apps, DB)
│   ├── urls.py             # Root URL configuration
│   ├── celery.py           # Celery app configuration
│   └── ...
├── users/                  # App for User Management
│   ├── models.py           # Custom User model with Roles
│   └── ...
├── courses/                # App for Course & Section Management
│   ├── models.py           # Course and Section models
│   └── ...
├── enrollment/             # App for Enrollment Logic
│   ├── models.py           # Enrollment model
│   └── ...
├── adbms_demo/             # App for ADBMS Concept Demonstrations
│   └── ...
├── docs/                   # Documentation
├── Dockerfile              # Docker image definition for Django
├── docker-compose.yml      # Service orchestration (Web, DB, Redis)
├── entrypoint.sh           # Container entrypoint script
├── manage.py               # Django management script
└── requirements.txt        # Python dependencies
```

## Database Schema

### 1. Users (`users.User`)
Extends Django's `AbstractUser`.
-   **Fields**:
    -   `role`: Enum (`STUDENT`, `INSTRUCTOR`, `ADMIN`).
    -   Standard Django Auth fields (username, password, email, etc.).

### 2. Courses (`courses.Course`)
Represents a generic course (metadata).
-   **Fields**:
    -   `code`: Unique course code (e.g., "CS101").
    -   `title`: Course name.
    -   `credits`: Number of credits.

### 3. Sections (`courses.Section`)
Represents a specific offering of a course in a semester.
-   **Fields**:
    -   `course`: FK to `Course`.
    -   `instructor`: FK to `User` (Role: INSTRUCTOR).
    -   `semester`: String (e.g., "Fall 2025").
    -   `capacity`: Max seats available.
    -   `version`: Integer (for Optimistic Locking demos).

### 4. Enrollments (`enrollment.Enrollment`)
Links a Student to a Section.
-   **Fields**:
    -   `student`: FK to `User`.
    -   `section`: FK to `Section`.
    -   `grade`: Char field for grade.
-   **Constraints**:
    -   `unique_together`: (`student`, `section`) - A student cannot enroll in the same section twice.

## Technology Stack Details

-   **Backend Framework**: Django 5.x
-   **Database**: PostgreSQL 16
    -   Used for its advanced concurrency control and locking features.
-   **Async Task Queue**: Celery + Redis
    -   Used for background processing and workload generation for benchmarking.
-   **Containerization**: Docker
    -   Ensures consistent environment for ADBMS demos (isolation levels, replication).

## Key Configuration

-   **Environment Variables**: Managed via `django-environ`.
-   **Database Connection**: Configured via `DATABASE_URL` in `.env`.
-   **Celery**: Configured in `config/settings.py` and `config/celery.py`.
