from rest_framework import serializers
from .models import Enrollment, Waitlist
from courses.serializers import SectionSerializer

class EnrollmentSerializer(serializers.ModelSerializer):
    section_details = SectionSerializer(source='section', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'section', 'section_details', 'enrolled_at', 'grade']
        read_only_fields = ['student', 'enrolled_at', 'grade']


class WaitlistSerializer(serializers.ModelSerializer):
    section_details = SectionSerializer(source='section', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)
    position = serializers.SerializerMethodField()
    waitlist_size = serializers.SerializerMethodField()

    class Meta:
        model = Waitlist
        fields = ['id', 'student', 'student_name', 'section', 'section_details', 'joined_at', 'position', 'waitlist_size', 'notified']
        read_only_fields = ['student', 'joined_at', 'notified']

    def get_position(self, obj):
        """Calculate the student's position in the waitlist."""
        return obj.get_position()
    
    def get_waitlist_size(self, obj):
        """Get total number of students in the waitlist for this section."""
        return Waitlist.objects.filter(section=obj.section).count()

