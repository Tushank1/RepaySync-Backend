from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from .models import User
from .audit import create_audit_log
from drf_spectacular.utils import extend_schema
from .docs_serializers import AssignReportingSerializer

@extend_schema(request=AssignReportingSerializer)
class AssignReportingAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only SuperAdmin can assign reporting")

        user_id = request.data.get("user_id")
        reporting_to_id = request.data.get("reporting_to_id")

        if not user_id or not reporting_to_id:
            return Response(
                {"error": "user_id and reporting_to_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(id=user_id, is_active=True)
            reporting_to = User.objects.get(id=reporting_to_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        user.manager = reporting_to
        user.save()

        create_audit_log(
            request.user,
            "updated reporting manager",
            f"{user.username} -> {reporting_to.username}"
        )

        return Response({
            "message": "Reporting updated successfully"
        })