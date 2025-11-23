from django.test import TestCase
from django.contrib.auth import get_user_model
from courses.models import Course, Section
from enrollment.models import Enrollment, Waitlist
from adbms_demo.models import AuditLog
from django.db import connection

User = get_user_model()

class TriggerTests(TestCase):
    def setUp(self):
        # Create test users
        self.student = User.objects.create_user(username='student1', password='password', role='STUDENT')
        self.instructor = User.objects.create_user(username='instructor1', password='password', role='INSTRUCTOR')
        
        # Create initial course and section
        self.course = Course.objects.create(
            code='CS101',
            title='Intro to CS',
            description='Basic CS',
            credits=3
        )
        self.section = Section.objects.create(
            course=self.course,
            semester='Fall 2025',
            capacity=30,
            room_number='101',
            schedule='Mon 10:00',
            instructor=self.instructor
        )

    def test_enrollment_triggers(self):
        """Test triggers on Enrollment table"""
        # Test INSERT trigger
        enrollment = Enrollment.objects.create(student=self.student, section=self.section)
        
        log = AuditLog.objects.filter(table_name='enrollment_enrollment', operation='INSERT').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, enrollment.id)
        self.assertIn('New enrollment', log.change_summary)
        
        # Test UPDATE trigger
        enrollment.grade = 'A'
        enrollment.save()
        
        log = AuditLog.objects.filter(table_name='enrollment_enrollment', operation='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, enrollment.id)
        self.assertIn('Grade changed', log.change_summary)
        self.assertEqual(log.new_data['grade'], 'A')
        
        # Test DELETE trigger
        enrollment_id = enrollment.id
        enrollment.delete()
        
        log = AuditLog.objects.filter(table_name='enrollment_enrollment', operation='DELETE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, enrollment_id)
        self.assertIn('Enrollment deleted', log.change_summary)

    def test_course_triggers(self):
        """Test triggers on Course table"""
        # Test INSERT trigger
        course = Course.objects.create(code='CS102', title='Data Structures', credits=4)
        
        log = AuditLog.objects.filter(table_name='courses_course', operation='INSERT').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, course.id)
        
        # Test UPDATE trigger
        course.credits = 3
        course.save()
        
        log = AuditLog.objects.filter(table_name='courses_course', operation='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertIn('Credits changed', log.change_summary)
        
        # Test DELETE trigger
        course_id = course.id
        course.delete()
        
        log = AuditLog.objects.filter(table_name='courses_course', operation='DELETE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, course_id)

    def test_section_triggers(self):
        """Test triggers on Section table"""
        # Test INSERT trigger
        section = Section.objects.create(
            course=self.course,
            semester='Spring 2026',
            capacity=25,
            room_number='102',
            schedule='Tue 10:00'
        )
        
        log = AuditLog.objects.filter(table_name='courses_section', operation='INSERT').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, section.id)
        
        # Test UPDATE trigger
        section.capacity = 50
        section.save()
        
        log = AuditLog.objects.filter(table_name='courses_section', operation='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertIn('Capacity changed', log.change_summary)
        
        # Test DELETE trigger
        section_id = section.id
        section.delete()
        
        log = AuditLog.objects.filter(table_name='courses_section', operation='DELETE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, section_id)

    def test_waitlist_triggers(self):
        """Test triggers on Waitlist table"""
        # Test INSERT trigger
        waitlist = Waitlist.objects.create(student=self.student, section=self.section)
        
        log = AuditLog.objects.filter(table_name='enrollment_waitlist', operation='INSERT').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, waitlist.id)
        
        # Test UPDATE trigger
        waitlist.notified = True
        waitlist.save()
        
        log = AuditLog.objects.filter(table_name='enrollment_waitlist', operation='UPDATE').last()
        self.assertIsNotNone(log)
        self.assertIn('notified', log.change_summary)
        
        # Test DELETE trigger
        waitlist_id = waitlist.id
        waitlist.delete()
        
        log = AuditLog.objects.filter(table_name='enrollment_waitlist', operation='DELETE').last()
        self.assertIsNotNone(log)
        self.assertEqual(log.record_id, waitlist_id)
