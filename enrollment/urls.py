from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnrollmentViewSet, EnrollStudentView

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')

urlpatterns = [
    path('', include(router.urls)),
    path('enroll/', EnrollStudentView.as_view(), name='enroll-student'),
]
