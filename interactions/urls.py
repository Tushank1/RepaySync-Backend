from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import InteractionViewSet
from .query_apis import CustomerInteractionHistoryAPIView
from .upload_api import InteractionCSVUploadAPIView

router = DefaultRouter()
router.register("", InteractionViewSet, basename="interactions")

urlpatterns = [
    path("customer/<int:customer_id>/", CustomerInteractionHistoryAPIView.as_view()),
    path("upload-csv/", InteractionCSVUploadAPIView.as_view()),
]

urlpatterns += router.urls