# Smart Course Registration System - Setup Guide

This guide provides step-by-step instructions to set up and run the Smart Course Registration System locally using Docker.

## Prerequisites

- **Docker**: Ensure Docker is installed and running.
- **Docker Compose**: Ensure Docker Compose is installed (usually included with Docker Desktop/Engine).

## Installation & Running

1.  **Clone the Repository** (if applicable) or navigate to the project directory.

2.  **Environment Configuration**
    The project comes with a default `.env` file. Ensure it exists in the root directory with the following content:
    ```env
    DEBUG=1
    SECRET_KEY=django-insecure-change-me-in-prod
    ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
    DATABASE_URL=postgres://postgres:postgres@db:5432/course_db
    CELERY_BROKER_URL=redis://redis:6379/0
    CELERY_RESULT_BACKEND=redis://redis:6379/0
    ```

3.  **Build and Start Containers**
    Run the following command to build the Docker images and start the services (Web, Database, Redis):
    ```bash
    docker-compose up -d --build
    ```
    -   `web`: The Django application (running on port 8000).
    -   `db`: PostgreSQL 16 database (exposed on port 5432).
    -   `redis`: Redis for Celery task queue.

4.  **Apply Database Migrations**
    Once the containers are up, apply the database migrations to create the schema:
    ```bash
    docker-compose exec web python manage.py migrate
    ```

## User Management

### Creating a Superuser (Admin)
To access the Django Admin panel, you need a superuser. Run the following command:

```bash
docker-compose exec web python manage.py createsuperuser
```
Follow the prompts to set a username, email, and password.

**Quick Setup (Non-interactive):**
You can also create a superuser non-interactively using environment variables:
```bash
docker-compose exec -e DJANGO_SUPERUSER_USERNAME=admin -e DJANGO_SUPERUSER_EMAIL=admin@example.com -e DJANGO_SUPERUSER_PASSWORD=admin web python manage.py createsuperuser --noinput
```
*Credentials: `admin` / `admin`*

## Accessing the Application

-   **Web Application**: [http://localhost:8000/](http://localhost:8000/)
-   **Admin Panel**: [http://localhost:8000/admin/](http://localhost:8000/admin/)
-   **API Documentation (Swagger)**: [http://localhost:8000/api/docs/](http://localhost:8000/api/docs/)
-   **API Documentation (Redoc)**: [http://localhost:8000/api/redoc/](http://localhost:8000/api/redoc/)

## Development Commands

-   **Make Migrations** (after changing models):
    ```bash
    docker-compose exec web python manage.py makemigrations
    ```
-   **View Logs**:
    ```bash
    docker-compose logs -f web
    ```
-   **Shell Access**:
    ```bash
    docker-compose exec web python manage.py shell
    ```
