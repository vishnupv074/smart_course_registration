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
