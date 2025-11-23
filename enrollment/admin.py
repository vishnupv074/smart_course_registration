from django.contrib import admin
from .models import Enrollment, Waitlist


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ['student', 'section', 'enrolled_at', 'grade']
    list_filter = ['enrolled_at', 'section__semester']
    search_fields = ['student__username', 'student__email', 'section__course__code']
    raw_id_fields = ['student', 'section']


@admin.register(Waitlist)
class WaitlistAdmin(admin.ModelAdmin):
    list_display = ['student', 'section', 'joined_at', 'get_position_display', 'notified']
    list_filter = ['joined_at', 'notified', 'section__semester']
    search_fields = ['student__username', 'student__email', 'section__course__code']
    raw_id_fields = ['student', 'section']
    
    def get_position_display(self, obj):
        """Display the waitlist position."""
        return obj.get_position()
    get_position_display.short_description = 'Position'

