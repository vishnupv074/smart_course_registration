from rest_framework import serializers
from .models import Enrollment
from courses.serializers import SectionSerializer

class EnrollmentSerializer(serializers.ModelSerializer):
    section_details = SectionSerializer(source='section', read_only=True)
    student_name = serializers.CharField(source='student.get_full_name', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'student', 'student_name', 'section', 'section_details', 'enrolled_at', 'grade']
        read_only_fields = ['student', 'enrolled_at', 'grade']
