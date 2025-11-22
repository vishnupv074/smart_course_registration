from django.core.management.base import BaseCommand
from courses.models import Course, Section
from users.models import User
from django.db import transaction
import random
import string

class Command(BaseCommand):
    help = 'Seeds the database with large amount of data for benchmarking'

    def add_arguments(self, parser):
        parser.add_argument('--courses', type=int, default=10000, help='Number of courses to create')

    def handle(self, *args, **options):
        count = options['courses']
        self.stdout.write(f'Seeding {count} courses...')

        # Ensure we have an instructor
        instructor, _ = User.objects.get_or_create(username='benchmark_instructor', role='INSTRUCTOR')

        courses_to_create = []
        sections_to_create = []

        # Generate random data
        for i in range(count):
            code = f"CS{i:06d}"
            title = f"Course {i} " + ''.join(random.choices(string.ascii_uppercase, k=5))
            description = f"Description for course {i}. " + ' '.join([''.join(random.choices(string.ascii_lowercase, k=5)) for _ in range(10)])
            
            course = Course(code=code, title=title, description=description, credits=3)
            courses_to_create.append(course)
            
            if len(courses_to_create) >= 1000:
                Course.objects.bulk_create(courses_to_create)
                self.stdout.write(f'Created {i+1} courses...')
                courses_to_create = []

        if courses_to_create:
            Course.objects.bulk_create(courses_to_create)

        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} courses'))
