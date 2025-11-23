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


class AuditLog(models.Model):
    """
    Audit log for tracking all changes to critical tables.
    Populated automatically by database triggers (PL/pgSQL).
    """
    OPERATION_CHOICES = [
        ('INSERT', 'Insert'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
    ]
    
    table_name = models.CharField(
        max_length=100,
        help_text="Name of the audited table (e.g., 'enrollment_enrollment')"
    )
    operation = models.CharField(
        max_length=10,
        choices=OPERATION_CHOICES,
        help_text="Type of operation performed"
    )
    record_id = models.IntegerField(
        help_text="ID of the affected record"
    )
    old_data = models.JSONField(
        null=True,
        blank=True,
        help_text="Previous state of the record (for UPDATE/DELETE)"
    )
    new_data = models.JSONField(
        null=True,
        blank=True,
        help_text="New state of the record (for INSERT/UPDATE)"
    )
    changed_by = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Username or session info if available"
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the change occurred"
    )
    change_summary = models.TextField(
        blank=True,
        help_text="Human-readable description of the change"
    )
    
    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['table_name', '-changed_at']),
            models.Index(fields=['operation', '-changed_at']),
            models.Index(fields=['record_id', 'table_name']),
        ]
    
    def __str__(self):
        return f"{self.operation} on {self.table_name} (ID: {self.record_id}) at {self.changed_at}"

