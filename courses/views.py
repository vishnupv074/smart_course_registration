from rest_framework import viewsets, permissions
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.db import models
from .models import Course, Section
from .serializers import CourseSerializer, SectionSerializer
from .forms import CourseForm, SectionForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages

def course_list(request):
    # Get search query if provided
    search_query = request.GET.get('search', '').strip()
    
    # Filter courses based on search query
    if search_query:
        courses = Course.objects.filter(
            models.Q(code__icontains=search_query) | 
            models.Q(title__icontains=search_query) |
            models.Q(description__icontains=search_query)
        ).prefetch_related('sections__instructor').order_by('code')
    else:
        courses = Course.objects.prefetch_related('sections__instructor').all().order_by('code')
    
    # Paginate results (20 courses per page)
    paginator = Paginator(courses, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'courses/course_list.html', {
        'page_obj': page_obj,
        'search_query': search_query
    })

@login_required
def instructor_dashboard(request):
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, "Access denied. Instructor role required.")
        return redirect('home')
        
    sections = Section.objects.filter(instructor=request.user).select_related('course')
    
    # Get unique courses that the instructor is teaching
    course_ids = sections.values_list('course_id', flat=True).distinct()
    courses = Course.objects.filter(id__in=course_ids)
    
    return render(request, 'courses/instructor_dashboard.html', {
        'sections': sections,
        'courses': courses
    })

@login_required
def create_course(request):
    """Create a new course (instructor only)"""
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, "Access denied. Instructor role required.")
        return redirect('home')
    
    if request.method == 'POST':
        form = CourseForm(request.POST)
        if form.is_valid():
            course = form.save()
            messages.success(request, f"Course '{course.code}' created successfully!")
            return redirect('instructor-dashboard')
    else:
        form = CourseForm()
    
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Create'})

@login_required
def edit_course(request, pk):
    """Edit an existing course"""
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, "Access denied. Instructor role required.")
        return redirect('home')
    
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f"Course '{course.code}' updated successfully!")
            return redirect('instructor-dashboard')
    else:
        form = CourseForm(instance=course)
    
    return render(request, 'courses/course_form.html', {'form': form, 'action': 'Edit', 'course': course})

@login_required
def create_section(request):
    """Create a new section (instructor only)"""
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, "Access denied. Instructor role required.")
        return redirect('home')
    
    if request.method == 'POST':
        form = SectionForm(request.POST)
        if form.is_valid():
            section = form.save(commit=False)
            section.instructor = request.user  # Assign current user as instructor
            section.save()
            messages.success(request, f"Section for '{section.course.code}' created successfully!")
            return redirect('instructor-dashboard')
    else:
        form = SectionForm()
    
    return render(request, 'courses/section_form.html', {'form': form, 'action': 'Create'})

@login_required
def edit_section(request, pk):
    """Edit an existing section (only if user is the instructor)"""
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, "Access denied. Instructor role required.")
        return redirect('home')
    
    section = get_object_or_404(Section, pk=pk)
    
    # Check if the current user is the instructor for this section
    if section.instructor != request.user:
        messages.error(request, "You can only edit sections you are teaching.")
        return redirect('instructor-dashboard')
    
    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        if form.is_valid():
            form.save()
            messages.success(request, f"Section for '{section.course.code}' updated successfully!")
            return redirect('instructor-dashboard')
    else:
        form = SectionForm(instance=section)
    
    return render(request, 'courses/section_form.html', {'form': form, 'action': 'Edit', 'section': section})

@login_required
def view_section_students(request, pk):
    """View list of students enrolled in a section (instructor only)"""
    if request.user.role != 'INSTRUCTOR':
        messages.error(request, "Access denied. Instructor role required.")
        return redirect('home')
    
    section = get_object_or_404(Section, pk=pk)
    
    # Check if the current user is the instructor for this section
    if section.instructor != request.user:
        messages.error(request, "You can only view students for sections you are teaching.")
        return redirect('instructor-dashboard')
    
    # Get all enrollments for this section with student details
    enrollments = section.enrollments.select_related('student').order_by('student__username')
    
    context = {
        'section': section,
        'enrollments': enrollments,
        'enrolled_count': enrollments.count(),
    }
    
    return render(request, 'courses/section_students.html', context)

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
