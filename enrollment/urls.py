from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnrollmentViewSet, EnrollStudentView, drop_course

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')

urlpatterns = [
    path('', include(router.urls)),
    path('drop/<int:section_id>/', drop_course, name='drop-course'),
    path('enroll/', EnrollStudentView.as_view(), name='enroll-student'),
]
