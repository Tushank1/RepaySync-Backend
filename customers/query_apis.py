from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Customer
from .serializers import CustomerSerializer
from accounts.models import User
from drf_spectacular.utils import extend_schema

@extend_schema(responses=CustomerSerializer(many=True))
class CustomersByOfficerAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_customers_for_target(self, target_user):
        # collection officer
        if target_user.role == "collection_officer":
            return Customer.objects.filter(
                assigned_to=target_user,
                is_active=True
            )

        # manager
        if target_user.role == "manager":
            officer_ids = User.objects.filter(
                manager=target_user,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            return Customer.objects.filter(
                assigned_to__id__in=officer_ids,
                is_active=True
            )

        # super manager
        if target_user.role == "super_manager":
            manager_ids = User.objects.filter(
                manager=target_user,
                role="manager",
                is_active=True
            ).values_list("id", flat=True)

            officer_ids = User.objects.filter(
                manager__id__in=manager_ids,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            return Customer.objects.filter(
                assigned_to__id__in=officer_ids,
                is_active=True
            )

        return Customer.objects.none()

    def get(self, request, officer_id):
        user = request.user

        if user.role in ["collection_officer", "calling_agent"]:
            raise PermissionDenied("Permission denied")

        try:
            target = User.objects.get(id=officer_id, is_active=True)
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        # hierarchy validation
        if user.role == "super_manager":
            allowed_ids = User.objects.filter(
                manager=user,
                is_active=True
            ).values_list("id", flat=True)

            child_officer_ids = User.objects.filter(
                manager__id__in=allowed_ids,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            if target.id not in list(allowed_ids) + list(child_officer_ids):
                raise PermissionDenied("User not in your hierarchy")

        if user.role == "manager":
            if target.role != "collection_officer" or target.manager != user:
                raise PermissionDenied("User not in your team")

        customers = self.get_customers_for_target(target)

        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)

@extend_schema(responses=CustomerSerializer(many=True))
class MyAssignedCustomersAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        if user.role in ["admin", "calling_agent"]:
            raise PermissionDenied("Permission denied")

        if user.role == "collection_officer":
            customers = Customer.objects.filter(
                assigned_to=user,
                is_active=True
            )

        elif user.role == "manager":
            officer_ids = User.objects.filter(
                manager=user,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            customers = Customer.objects.filter(
                assigned_to__id__in=officer_ids,
                is_active=True
            )

        elif user.role == "super_manager":
            manager_ids = User.objects.filter(
                manager=user,
                role="manager",
                is_active=True
            ).values_list("id", flat=True)

            officer_ids = User.objects.filter(
                manager__id__in=manager_ids,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            customers = Customer.objects.filter(
                assigned_to__id__in=officer_ids,
                is_active=True
            )

        else:
            customers = Customer.objects.none()

        serializer = CustomerSerializer(customers, many=True)
        return Response(serializer.data)