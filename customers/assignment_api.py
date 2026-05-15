from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from .models import Customer
from accounts.models import User
from accounts.audit import create_audit_log
from drf_spectacular.utils import extend_schema
from .docs_serializers import (
    AssignCustomerSerializer,
    BulkAssignCustomerSerializer,
)

@extend_schema(request=AssignCustomerSerializer)
class AssignCustomerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only SuperAdmin can assign customers")

        customer_id = request.data.get("customer_id")
        officer_id = request.data.get("officer_id")

        if not customer_id or not officer_id:
            return Response(
                {"error": "customer_id and officer_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            customer = Customer.objects.get(id=customer_id, is_active=True)
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        try:
            officer = User.objects.get(id=officer_id, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        if officer.role != "collection_officer":
            return Response(
                {"error": "Customer can only be assigned to collection officer"},
                status=status.HTTP_400_BAD_REQUEST
            )

        customer.assigned_to = officer
        customer.save()
        
        create_audit_log(
            request.user,
            "assigned customer",
            f"Customer {customer.id} -> {officer.username}"
        )

        return Response({
            "message": "Customer assigned successfully",
            "customer_id": customer.id,
            "assigned_to": officer.username
        })
        
@extend_schema(request=BulkAssignCustomerSerializer)
class BulkAssignCustomerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != "admin":
            raise PermissionDenied("Only SuperAdmin can bulk assign customers")

        customer_ids = request.data.get("customer_ids", [])
        officer_id = request.data.get("officer_id")

        if not customer_ids or not officer_id:
            return Response(
                {"error": "customer_ids and officer_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            officer = User.objects.get(
                id=officer_id,
                role="collection_officer",
                is_active=True
            )
        except User.DoesNotExist:
            return Response(
                {"error": "Collection officer not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        customers = Customer.objects.filter(
            id__in=customer_ids,
            is_active=True
        )

        updated_count = customers.update(assigned_to=officer)
        
        create_audit_log(
            request.user,
            "bulk assigned customers",
            f"{updated_count} customers -> {officer.username}"
        )

        return Response({
            "message": "Bulk assignment successful",
            "assigned_to": officer.username,
            "total_customers_updated": updated_count
        })