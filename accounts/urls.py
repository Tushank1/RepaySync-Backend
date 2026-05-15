from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserViewSet
from .upload_api import UserCSVUploadAPIView
from .audit_views import AuditLogAPIView
from .reporting_api import AssignReportingAPIView
from .password_api import ChangePasswordAPIView, ForgotPasswordAPIView

router = DefaultRouter()
router.register("users", UserViewSet)

urlpatterns = [
    path("upload-csv/", UserCSVUploadAPIView.as_view(), name="user-upload-csv"),
    path("audit-logs/", AuditLogAPIView.as_view(), name="audit-logs"),
    path("assign-reporting/", AssignReportingAPIView.as_view()),
    path("change-password/", ChangePasswordAPIView.as_view()),
    path("forgot-password/", ForgotPasswordAPIView.as_view()),
]

urlpatterns += router.urls