from django.core.management.base import BaseCommand
from adbms_demo.models import NonPartitionedEnrollment, PartitionedEnrollment
from django.db import connection


class Command(BaseCommand):
    help = 'Seed partitioned and non-partitioned enrollment tables for benchmarking'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=100000, help='Number of records to create')

    def handle(self, *args, **options):
        count = options['count']
        
        self.stdout.write(f'Creating {count} enrollment records...')
        
        # Semesters for distribution
        semesters = ['Fall 2024', 'Spring 2025', 'Fall 2025', 'Spring 2026']
        course_codes = [f'CS{100 + i}' for i in range(50)]  # CS100, CS101, etc.
        
        # Clear existing data
        self.stdout.write('Clearing existing data...')
        NonPartitionedEnrollment.objects.all().delete()
        
        # For partitioned table, use raw SQL to delete
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM adbms_demo_partitionedenrollment")
        
        # Create batches for bulk insert
        batch_size = 1000
        non_partitioned_batch = []
        partitioned_batch = []
        
        for i in range(count):
            semester = semesters[i % len(semesters)]
            course = course_codes[i % len(course_codes)]
            student_name = f"Student_{i}"
            grade = ['A', 'B', 'C', None][i % 4]
            
            # Non-partitioned
            non_partitioned_batch.append(
                NonPartitionedEnrollment(
                    student_name=student_name,
                    course_code=course,
                    semester=semester,
                    grade=grade
                )
            )
            
            # Partitioned
            partitioned_batch.append(
                PartitionedEnrollment(
                    student_name=student_name,
                    course_code=course,
                    semester=semester,
                    grade=grade
                )
            )
            
            # Insert in batches
            if len(non_partitioned_batch) >= batch_size:
                NonPartitionedEnrollment.objects.bulk_create(non_partitioned_batch)
                
                # For partitioned, use raw SQL with parameterized query
                with connection.cursor() as cursor:
                    for p in partitioned_batch:
                        cursor.execute(
                            "INSERT INTO adbms_demo_partitionedenrollment (student_name, course_code, semester, grade) VALUES (%s, %s, %s, %s)",
                            [p.student_name, p.course_code, p.semester, p.grade]
                        )
                
                non_partitioned_batch = []
                partitioned_batch = []
                
                if (i + 1) % 10000 == 0:
                    self.stdout.write(f'  ... {i + 1} records created')
        
        # Insert remaining
        if non_partitioned_batch:
            NonPartitionedEnrollment.objects.bulk_create(non_partitioned_batch)
            
            with connection.cursor() as cursor:
                for p in partitioned_batch:
                    cursor.execute(
                        "INSERT INTO adbms_demo_partitionedenrollment (student_name, course_code, semester, grade) VALUES (%s, %s, %s, %s)",
                        [p.student_name, p.course_code, p.semester, p.grade]
                    )
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created {count} records in both tables!'))
