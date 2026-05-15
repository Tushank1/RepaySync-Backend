from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from .models import Customer
from .serializers import CustomerSerializer
from django.db.models import Q
from accounts.models import User
from accounts.audit import create_audit_log
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

@extend_schema(
    parameters=[
        OpenApiParameter(
            name="search",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Search customers by name or phone"
        ),
        OpenApiParameter(
            name="disposition",
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Filter by latest disposition"
        ),
    ]
)
class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [IsAuthenticated]

    def _can_create_update(self):
        return self.request.user.role in [
            "admin",
            "super_manager",
            "manager",
            "collection_officer"
        ]

    def _can_delete(self):
        return self.request.user.role in [
            "admin",
            "super_manager"
        ]

    def get_queryset(self):
        user = self.request.user

        if user.role in ["admin", "calling_agent"]:
            queryset = Customer.objects.filter(is_active=True)

        elif user.role == "collection_officer":
            queryset = Customer.objects.filter(
                assigned_to=user,
                is_active=True
            )

        elif user.role == "manager":
            officer_ids = User.objects.filter(
                manager=user,
                role="collection_officer",
                is_active=True
            ).values_list("id", flat=True)

            queryset = Customer.objects.filter(
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

            queryset = Customer.objects.filter(
                assigned_to__id__in=officer_ids,
                is_active=True
            )

        else:
            queryset = Customer.objects.none()

        disposition = self.request.query_params.get("disposition")
        search = self.request.query_params.get("search")

        if disposition:
            queryset = queryset.filter(latest_disposition=disposition)

        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(phone__icontains=search)
            )

        return queryset

    def perform_create(self, serializer):
        user = self.request.user

        if not self._can_create_update():
            raise PermissionDenied("Permission denied")

        assigned_to = serializer.validated_data.get("assigned_to")

        if user.role == "collection_officer":
            assigned_to = user

        elif user.role == "manager":
            if not assigned_to:
                raise PermissionDenied(
                    "assigned_to field is required for manager"
                )

            if assigned_to.manager != user:
                raise PermissionDenied(
                    "Can assign only to your team"
                )

        elif user.role == "super_manager":
            if not assigned_to:
                raise PermissionDenied(
                    "assigned_to field is required for super manager"
                )

            if (
                assigned_to.manager is None or
                assigned_to.manager.manager != user
            ):
                raise PermissionDenied(
                    "Can assign only to your hierarchy"
                )

        customer = serializer.save(assigned_to=assigned_to)

        create_audit_log(
            user,
            "created customer",
            f"Customer {customer.id}"
        )

    def create(self, request, *args, **kwargs):
        if not self._can_create_update():
            raise PermissionDenied("Permission denied")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if not self._can_create_update():
            raise PermissionDenied("Permission denied")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not self._can_create_update():
            raise PermissionDenied("Permission denied")
        return super().partial_update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if not self._can_delete():
            raise PermissionDenied("Permission denied")
        instance.is_active = False
        instance.save()