from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from users.models import User
from courses.models import Course, Section
from enrollment.models import Enrollment
from admin_dashboard.utils import (
    check_database_health,
    get_enrollment_trends,
    get_popular_courses,
    get_seat_utilization
)


class AdminDashboardViewTests(TestCase):
    """Test cases for admin dashboard views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Create users
        self.admin_user = User.objects.create_user(
            username='admin',
            password='testpass123',
            role='ADMIN'
        )
        
        self.student_user = User.objects.create_user(
            username='student',
            password='testpass123',
            role='STUDENT'
        )
        
        self.instructor_user = User.objects.create_user(
            username='instructor',
            password='testpass123',
            role='INSTRUCTOR'
        )
    
    def test_admin_dashboard_requires_login(self):
        """Test that dashboard requires authentication"""
        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_admin_dashboard_requires_admin_role(self):
        """Test that only admin users can access dashboard"""
        # Try as student
        self.client.login(username='student', password='testpass123')
        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # Try as instructor
        self.client.logout()
        self.client.login(username='instructor', password='testpass123')
        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.status_code, 302)  # Redirect
    
    def test_admin_dashboard_accessible_to_admin(self):
        """Test that admin users can access dashboard"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin-dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin_dashboard/dashboard.html')
    
    def test_dashboard_context_data(self):
        """Test that dashboard provides correct context data"""
        self.client.login(username='admin', password='testpass123')
        response = self.client.get(reverse('admin-dashboard'))
        
        # Check that all required context keys are present
        self.assertIn('statistics', response.context)
        self.assertIn('analytics', response.context)
        self.assertIn('system_health', response.context)
        self.assertIn('recent_enrollments', response.context)


class UtilityFunctionsTests(TestCase):
    """Test cases for utility functions"""
    
    def setUp(self):
        """Set up test data"""
        # Create test course and section
        self.course = Course.objects.create(
            code='CS101',
            title='Introduction to Computer Science',
            description='Basic CS course',
            credits=3
        )
        
        self.instructor = User.objects.create_user(
            username='instructor',
            password='testpass123',
            role='INSTRUCTOR'
        )
        
        self.section = Section.objects.create(
            course=self.course,
            instructor=self.instructor,
            semester='Fall 2024',
            capacity=30,
            room_number='101',
            schedule='Mon/Wed 10:00-11:30'
        )
        
        # Create test students and enrollments
        for i in range(5):
            student = User.objects.create_user(
                username=f'student{i}',
                password='testpass123',
                role='STUDENT'
            )
            Enrollment.objects.create(
                student=student,
                section=self.section
            )
    
    def test_database_health_check(self):
        """Test database health check function"""
        result = check_database_health()
        self.assertTrue(result['status'])
        self.assertIsNotNone(result['response_time'])
        self.assertIn('healthy', result['message'].lower())
    
    def test_get_enrollment_trends(self):
        """Test enrollment trends function"""
        trends = get_enrollment_trends(days=30)
        self.assertIsInstance(trends, list)
        # Should have at least today's enrollments
        self.assertGreaterEqual(len(trends), 1)
    
    def test_get_popular_courses(self):
        """Test popular courses function"""
        popular = get_popular_courses(limit=10)
        self.assertIsInstance(popular, list)
        self.assertGreaterEqual(len(popular), 1)
        
        # Check structure of returned data
        if len(popular) > 0:
            self.assertIn('course_code', popular[0])
            self.assertIn('course_title', popular[0])
            self.assertIn('enrollment_count', popular[0])
    
    def test_get_seat_utilization(self):
        """Test seat utilization function"""
        utilization = get_seat_utilization()
        
        self.assertIn('total_seats', utilization)
        self.assertIn('filled_seats', utilization)
        self.assertIn('utilization_percentage', utilization)
        
        # Verify calculations
        self.assertEqual(utilization['total_seats'], 30)
        self.assertEqual(utilization['filled_seats'], 5)
        expected_percentage = round((5 / 30) * 100, 2)
        self.assertEqual(utilization['utilization_percentage'], expected_percentage)
