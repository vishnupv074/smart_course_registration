from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EnrollmentViewSet, EnrollStudentView, WaitlistViewSet,
    drop_course, my_waitlists, leave_waitlist
)

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'waitlists', WaitlistViewSet, basename='waitlist')

urlpatterns = [
    path('', include(router.urls)),
    path('drop/<int:section_id>/', drop_course, name='drop-course'),
    path('enroll/', EnrollStudentView.as_view(), name='enroll-student'),
    path('my-waitlists/', my_waitlists, name='my-waitlists'),
    path('waitlist/leave/<int:waitlist_id>/', leave_waitlist, name='leave-waitlist'),
]

