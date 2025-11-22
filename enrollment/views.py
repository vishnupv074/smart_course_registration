from rest_framework import viewsets, permissions, status, views
from rest_framework.response import Response
from django.db import transaction
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from .models import Enrollment
from .serializers import EnrollmentSerializer
from courses.models import Section

@login_required
def my_enrollments(request):
    enrollments = Enrollment.objects.filter(student=request.user).select_related('section', 'section__course', 'section__instructor')
    return render(request, 'enrollment/my_enrollments.html', {'enrollments': enrollments})

class EnrollmentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'STUDENT':
            return Enrollment.objects.filter(student=user)
        elif user.role == 'INSTRUCTOR':
            return Enrollment.objects.filter(section__instructor=user)
        return Enrollment.objects.all()

class EnrollStudentView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        section_id = request.data.get('section_id')
        student = request.user

        if student.role != 'STUDENT':
            return Response({'error': 'Only students can enroll'}, status=status.HTTP_403_FORBIDDEN)

        # ACID Transaction Start
        try:
            with transaction.atomic():
                # Lock the section row for update to prevent race conditions
                # This is a pessimistic lock (SELECT ... FOR UPDATE)
                section = Section.objects.select_for_update().get(id=section_id)

                # Check if already enrolled
                if Enrollment.objects.filter(student=student, section=section).exists():
                    return Response({'error': 'Already enrolled in this section'}, status=status.HTTP_400_BAD_REQUEST)

                # Check capacity
                current_enrollment_count = Enrollment.objects.filter(section=section).count()
                if current_enrollment_count >= section.capacity:
                    return Response({'error': 'Section is full'}, status=status.HTTP_400_BAD_REQUEST)

                # Create enrollment
                enrollment = Enrollment.objects.create(student=student, section=section)
                
                serializer = EnrollmentSerializer(enrollment)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Section.DoesNotExist:
            return Response({'error': 'Section not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
