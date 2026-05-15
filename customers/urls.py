from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet
from .assignment_api import AssignCustomerAPIView, BulkAssignCustomerAPIView
from .query_apis import CustomersByOfficerAPIView, MyAssignedCustomersAPIView
from .upload_api import CustomerCSVUploadAPIView

router = DefaultRouter()
router.register("", CustomerViewSet, basename="customers")

urlpatterns = [
    path("assign/", AssignCustomerAPIView.as_view(), name="assign-customer"),
    path("bulk-assign/", BulkAssignCustomerAPIView.as_view(), name="bulk-assign-customer"),
    path("upload-csv/", CustomerCSVUploadAPIView.as_view(), name="customer-upload-csv"),
    path("by-officer/<int:officer_id>/", CustomersByOfficerAPIView.as_view()),
    path("my-assigned/", MyAssignedCustomersAPIView.as_view()),
]

urlpatterns += router.urls