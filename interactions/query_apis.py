from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Interaction
from .serializers import InteractionSerializer
from drf_spectacular.utils import extend_schema
from customers.models import Customer

@extend_schema(responses=InteractionSerializer(many=True))
class CustomerInteractionHistoryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def can_access_customer(self, user, customer):
        # admin + calling agent => all
        if user.role in ["admin", "calling_agent"]:
            return True

        # customer not assigned
        if not customer.assigned_to:
            return False

        # collection officer
        if user.role == "collection_officer":
            return customer.assigned_to == user

        # manager
        if user.role == "manager":
            return customer.assigned_to.manager == user

        # super manager
        if user.role == "super_manager":
            return (
                customer.assigned_to.manager and
                customer.assigned_to.manager.manager == user
            )

        return False

    def get(self, request, customer_id):
        try:
            customer = Customer.objects.get(
                id=customer_id,
                is_active=True
            )
        except Customer.DoesNotExist:
            return Response(
                {"error": "Customer not found"},
                status=404
            )

        if not self.can_access_customer(request.user, customer):
            raise PermissionDenied("You cannot access this customer")

        interactions = Interaction.objects.filter(
            customer=customer
        ).order_by("-created_at")

        serializer = InteractionSerializer(interactions, many=True)
        return Response(serializer.data)