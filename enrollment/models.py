from django.db import models
from django.conf import settings

class Enrollment(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    section = models.ForeignKey(
        'courses.Section', 
        on_delete=models.CASCADE, 
        related_name='enrollments'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        unique_together = ('student', 'section')
        indexes = [
            models.Index(fields=['student', 'section']),
        ]

    def __str__(self):
        return f"{self.student.username} -> {self.section}"


class Waitlist(models.Model):
    """
    Tracks students waiting for full course sections.
    When a seat becomes available, the first student in the waitlist (FIFO) is automatically enrolled.
    """
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='waitlists'
    )
    section = models.ForeignKey(
        'courses.Section',
        on_delete=models.CASCADE,
        related_name='waitlists'
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(
        default=False,
        help_text="Whether the student has been notified of enrollment"
    )

    class Meta:
        unique_together = ('student', 'section')
        ordering = ['joined_at']  # FIFO order - first in, first out
        indexes = [
            models.Index(fields=['section', 'joined_at']),
            models.Index(fields=['student']),
        ]

    def __str__(self):
        return f"{self.student.username} waiting for {self.section}"
    
    def get_position(self):
        """Returns the position of this student in the waitlist (1-indexed)."""
        return Waitlist.objects.filter(
            section=self.section,
            joined_at__lt=self.joined_at
        ).count() + 1
