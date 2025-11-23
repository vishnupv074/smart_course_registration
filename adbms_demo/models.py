from django.db import models

class NonPartitionedEnrollment(models.Model):
    """
    Standard table for benchmarking comparison.
    """
    student_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    grade = models.CharField(max_length=2, blank=True, null=True)

    def __str__(self):
        return f"{self.student_name} - {self.course_code} ({self.semester})"

class PartitionedEnrollment(models.Model):
    """
    Partitioned table (PARTITION BY LIST (semester)).
    Managed manually via migrations.
    """
    id = models.AutoField(primary_key=True) # Needed for Django, though partitioning might complicate PKs
    student_name = models.CharField(max_length=100)
    course_code = models.CharField(max_length=20)
    semester = models.CharField(max_length=20)
    grade = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        managed = False # We create this manually to add PARTITION BY
        db_table = 'adbms_demo_partitionedenrollment'
