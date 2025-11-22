from rest_framework import viewsets, permissions
from django.shortcuts import render
from .models import Course, Section
from .serializers import CourseSerializer, SectionSerializer

def course_list(request):
    courses = Course.objects.prefetch_related('sections__instructor').all()
    return render(request, 'courses/course_list.html', {'courses': courses})

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_staff

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAdminOrReadOnly]

class SectionViewSet(viewsets.ModelViewSet):
    queryset = Section.objects.all()
    serializer_class = SectionSerializer
    permission_classes = [IsAdminOrReadOnly]
