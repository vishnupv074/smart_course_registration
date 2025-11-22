from django.db import models
from django.conf import settings

class Course(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    credits = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.title}"

class Section(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='sections')
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'role': 'INSTRUCTOR'},
        related_name='teaching_sections'
    )
    semester = models.CharField(max_length=20) # e.g., "Fall 2025"
    capacity = models.PositiveIntegerField()
    room_number = models.CharField(max_length=50)
    schedule = models.CharField(max_length=100, help_text="e.g., Mon/Wed 10:00-11:30")
    
    # For concurrency control demos
    version = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.course.code} - {self.semester} (Sec {self.id})"
