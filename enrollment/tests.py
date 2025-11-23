from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from courses.models import Course, Section
from enrollment.models import Enrollment, Waitlist
from enrollment.tasks import process_waitlist
from django.db import transaction
import time

User = get_user_model()


class WaitlistTestCase(TransactionTestCase):
    """Test cases for waitlist functionality"""
    
    def setUp(self):
        """Set up test data"""
        # Create users
        self.student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='testpass123',
            role='STUDENT'
        )
        self.student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='testpass123',
            role='STUDENT'
        )
        self.student3 = User.objects.create_user(
            username='student3',
            email='student3@test.com',
            password='testpass123',
            role='STUDENT'
        )
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='INSTRUCTOR'
        )
        
        # Create course and section with capacity of 1
        self.course = Course.objects.create(
            code='CS101',
            title='Introduction to Computer Science',
            description='Basic CS course',
            credits=3
        )
        self.section = Section.objects.create(
            course=self.course,
            instructor=self.instructor,
            semester='Fall 2024',
            capacity=1,  # Only 1 seat
            room_number='Room 101',
            schedule='Mon/Wed 10:00-11:30'
        )
    
    def test_join_waitlist_when_full(self):
        """Test that student is added to waitlist when section is full"""
        # Fill the section
        Enrollment.objects.create(student=self.student1, section=self.section)
        
        # Try to enroll student2 - should be added to waitlist
        self.client.login(username='student2', password='testpass123')
        response = self.client.post('/api/enroll/', {
            'section_id': self.section.id
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['status'], 'waitlisted')
        
        # Verify student2 is in waitlist
        self.assertTrue(Waitlist.objects.filter(student=self.student2, section=self.section).exists())
        
    def test_cannot_join_waitlist_if_enrolled(self):
        """Test that enrolled students cannot join waitlist"""
        # Enroll student1
        Enrollment.objects.create(student=self.student1, section=self.section)
        
        # Try to add student1 to waitlist
        self.client.login(username='student1', password='testpass123')
        response = self.client.post('/api/enroll/', {
            'section_id': self.section.id
        }, content_type='application/json')
        
        self.assertEqual(response.status_code, 400)
        self.assertIn('Already enrolled', response.json()['error'])
    
    def test_auto_enroll_from_waitlist(self):
        """Test automatic enrollment when seat becomes available"""
        # Fill the section
        enrollment1 = Enrollment.objects.create(student=self.student1, section=self.section)
        
        # Add student2 to waitlist
        Waitlist.objects.create(student=self.student2, section=self.section)
        
        # Student1 drops the course
        enrollment1.delete()
        
        # Process waitlist
        result = process_waitlist(self.section.id)
        
        # Verify student2 is now enrolled
        self.assertTrue(Enrollment.objects.filter(student=self.student2, section=self.section).exists())
        
        # Verify student2 is removed from waitlist
        self.assertFalse(Waitlist.objects.filter(student=self.student2, section=self.section).exists())
    
    def test_waitlist_fifo_order(self):
        """Test that waitlist processes in FIFO order"""
        # Fill the section
        enrollment1 = Enrollment.objects.create(student=self.student1, section=self.section)
        
        # Add students to waitlist in order
        waitlist2 = Waitlist.objects.create(student=self.student2, section=self.section)
        time.sleep(0.01)  # Ensure different timestamps
        waitlist3 = Waitlist.objects.create(student=self.student3, section=self.section)
        
        # Verify positions
        self.assertEqual(waitlist2.get_position(), 1)
        self.assertEqual(waitlist3.get_position(), 2)
        
        # Student1 drops
        enrollment1.delete()
        
        # Process waitlist
        process_waitlist(self.section.id)
        
        # Verify student2 (first in waitlist) is enrolled
        self.assertTrue(Enrollment.objects.filter(student=self.student2, section=self.section).exists())
        
        # Verify student3 is still in waitlist
        self.assertTrue(Waitlist.objects.filter(student=self.student3, section=self.section).exists())
        
        # Verify student3 is now first in waitlist
        waitlist3.refresh_from_db()
        self.assertEqual(waitlist3.get_position(), 1)
    
    def test_leave_waitlist(self):
        """Test that students can leave waitlist"""
        # Fill section and add student2 to waitlist
        Enrollment.objects.create(student=self.student1, section=self.section)
        waitlist = Waitlist.objects.create(student=self.student2, section=self.section)
        
        # Student2 leaves waitlist
        self.client.login(username='student2', password='testpass123')
        response = self.client.post(f'/api/waitlist/leave/{waitlist.id}/')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        
        # Verify student2 is removed from waitlist
        self.assertFalse(Waitlist.objects.filter(student=self.student2, section=self.section).exists())
    
    def test_schedule_conflict_prevents_auto_enrollment(self):
        """Test that schedule conflicts prevent automatic enrollment from waitlist"""
        # Create another section with conflicting schedule
        conflicting_section = Section.objects.create(
            course=self.course,
            instructor=self.instructor,
            semester='Fall 2024',
            capacity=10,
            room_number='Room 102',
            schedule='Mon/Wed 10:30-12:00'  # Overlaps with original section
        )
        
        # Enroll student2 in conflicting section
        Enrollment.objects.create(student=self.student2, section=conflicting_section)
        
        # Fill original section
        enrollment1 = Enrollment.objects.create(student=self.student1, section=self.section)
        
        # Add student2 to waitlist for original section
        Waitlist.objects.create(student=self.student2, section=self.section)
        
        # Student1 drops
        enrollment1.delete()
        
        # Process waitlist
        result = process_waitlist(self.section.id)
        
        # Verify student2 is NOT enrolled (due to conflict)
        self.assertFalse(Enrollment.objects.filter(student=self.student2, section=self.section).exists())
        
        # Verify student2 is removed from waitlist
        self.assertFalse(Waitlist.objects.filter(student=self.student2, section=self.section).exists())
        
        # Verify result message mentions conflict
        self.assertIn('conflict', result.lower())


class WaitlistViewTestCase(TestCase):
    """Test cases for waitlist views"""
    
    def setUp(self):
        """Set up test data"""
        self.student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='STUDENT'
        )
        self.instructor = User.objects.create_user(
            username='instructor',
            email='instructor@test.com',
            password='testpass123',
            role='INSTRUCTOR'
        )
        self.course = Course.objects.create(
            code='CS101',
            title='Introduction to Computer Science',
            description='Basic CS course',
            credits=3
        )
        self.section = Section.objects.create(
            course=self.course,
            instructor=self.instructor,
            semester='Fall 2024',
            capacity=1,
            room_number='Room 101',
            schedule='Mon/Wed 10:00-11:30'
        )
    
    def test_my_waitlists_view(self):
        """Test my_waitlists view displays waitlist entries"""
        # Add student to waitlist
        Waitlist.objects.create(student=self.student, section=self.section)
        
        # Login and access view
        self.client.login(username='student', password='testpass123')
        response = self.client.get('/api/my-waitlists/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'CS101')
        self.assertContains(response, 'My Waitlists')
    
    def test_my_enrollments_shows_waitlists(self):
        """Test that my_enrollments view shows waitlist entries"""
        # Add student to waitlist
        Waitlist.objects.create(student=self.student, section=self.section)
        
        # Login and access view
        self.client.login(username='student', password='testpass123')
        response = self.client.get('/my-enrollments/')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'My Waitlists')
