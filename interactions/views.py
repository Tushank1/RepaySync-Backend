from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Interaction
from .serializers import InteractionSerializer
from rest_framework.exceptions import PermissionDenied
from accounts.models import User
from accounts.audit import create_audit_log
from django.db import models

class InteractionViewSet(viewsets.ModelViewSet):
    serializer_class = InteractionSerializer
    permission_classes = [IsAuthenticated]
    queryset = Interaction.objects.all().order_by("-created_at")

    def _can_access_customer(self, user, customer):
        if user.role in ["admin", "calling_agent"]:
            return True

        if user.role == "collection_officer":
            return customer.assigned_to == user

        if user.role == "manager":
            officers = User.objects.filter(
                manager=user,
                role="collection_officer",
                is_active=True
            )
            return customer.assigned_to in officers

        if user.role == "super_manager":
            managers = User.objects.filter(
                manager=user,
                role="manager",
                is_active=True
            )

            officers = User.objects.filter(
                manager__in=managers,
                role="collection_officer",
                is_active=True
            )

            return customer.assigned_to in officers

        return False
    
    def get_queryset(self):
        user = self.request.user

        if user.role in ["admin", "calling_agent"]:
            return Interaction.objects.all().order_by("-created_at")

        if user.role == "collection_officer":
            return Interaction.objects.filter(
                customer__assigned_to=user
            ).order_by("-created_at")

        if user.role == "manager":
            officer_ids = User.objects.filter(
                manager=user,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            return Interaction.objects.filter(
                customer__assigned_to__id__in=officer_ids
            ).order_by("-created_at")

        if user.role == "super_manager":
            manager_ids = User.objects.filter(
                manager=user,
                role="manager",
                is_active=True
            ).values_list("id", flat=True)

            officer_ids = User.objects.filter(
                models.Q(manager=user, role="collection_officer") |
                models.Q(manager__id__in=manager_ids, role="collection_officer"),
                is_active=True
            ).values_list("id", flat=True)

            return Interaction.objects.filter(
                customer__assigned_to__id__in=officer_ids
            ).order_by("-created_at")

        return Interaction.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        customer = serializer.validated_data["customer"]

        if not self._can_access_customer(user, customer):
            raise PermissionDenied("You cannot update this customer")

        team = "calling" if user.role == "calling_agent" else "field"

        interaction = serializer.save(
            updated_by=user,
            team=team
        )
        
        create_audit_log(
            user,
            "created interaction",
            f"Customer {interaction.customer.id}"
        )