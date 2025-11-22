from rest_framework import serializers
from .models import Course, Section
from users.serializers import UserSerializer

class SectionSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.get_full_name', read_only=True)
    course_code = serializers.CharField(source='course.code', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = Section
        fields = ['id', 'course', 'course_code', 'course_title', 'instructor', 'instructor_name', 
                  'semester', 'capacity', 'room_number', 'schedule', 'version']
        read_only_fields = ['version']

class CourseSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'code', 'title', 'description', 'credits', 'sections', 'created_at']
