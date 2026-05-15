from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import AuditLog
from .serializers import AuditLogSerializer
from drf_spectacular.utils import extend_schema
from rest_framework.generics import ListAPIView

@extend_schema(responses=AuditLogSerializer(many=True))
class AuditLogAPIView(ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        if self.request.user.role != "admin":
            raise PermissionDenied("Only SuperAdmin can view audit logs")

        return AuditLog.objects.all().order_by("-timestamp")
