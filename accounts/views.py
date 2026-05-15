from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from django.db import models
from .models import User
from .serializers import UserSerializer
from rest_framework.authtoken.views import ObtainAuthToken
from django.contrib.auth import authenticate, get_user_model
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import extend_schema
from .docs_serializers import LoginSerializer
from rest_framework.permissions import AllowAny

User = get_user_model()

class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]

    def _can_delete(self):
        return self.request.user.role in ["admin", "super_manager"]

    def get_queryset(self):
        user = self.request.user

        if user.role == "admin":
            return User.objects.filter(
                is_active=True
            ).exclude(id=user.id)

        if user.role == "super_manager":
            manager_ids = User.objects.filter(
                manager=user,
                role="manager",
                is_active=True
            ).values_list("id", flat=True)

            return User.objects.filter(
                is_active=True
            ).exclude(id=user.id).filter(
                (
                    models.Q(id__in=manager_ids)
                ) |
                (
                    models.Q(
                        manager__id__in=manager_ids,
                        role="collection_officer"
                    )
                )
            )

        if user.role == "manager":
            return User.objects.filter(
                manager=user,
                role="collection_officer",
                is_active=True
            )

        return User.objects.none()

    def perform_create(self, serializer):
        current_user = self.request.user
        role = serializer.validated_data.get("role")

        if current_user.role == "admin":
            serializer.save()
            return

        if current_user.role == "super_manager":
            if role == "manager":
                serializer.save(manager=current_user)
                return

            if role == "collection_officer":
                manager_id = self.request.data.get("manager")

                if not manager_id:
                    raise PermissionDenied(
                        "manager field is required for collection officer"
                    )

                try:
                    manager_user = User.objects.get(
                        id=manager_id,
                        role="manager",
                        manager=current_user,
                        is_active=True
                    )
                except User.DoesNotExist:
                    raise PermissionDenied(
                        "Manager must belong to your hierarchy"
                    )

                serializer.save(manager=manager_user)
                return

            raise PermissionDenied(
                "Super manager can create only manager or collection officer"
            )

        if current_user.role == "manager":
            if role != "collection_officer":
                raise PermissionDenied(
                    "Manager can create only collection officer"
                )

            serializer.save(manager=current_user)
            return

        raise PermissionDenied("Permission denied")

    def create(self, request, *args, **kwargs):
        if request.user.role not in ["admin", "super_manager", "manager"]:
            raise PermissionDenied("Permission denied")
        return super().create(request, *args, **kwargs)

    def update(self, request, *args, **kwargs):
        if request.user.role not in ["admin", "super_manager", "manager"]:
            raise PermissionDenied("Permission denied")
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role not in ["admin", "super_manager", "manager"]:
            raise PermissionDenied("Permission denied")
        return super().partial_update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        if not self._can_delete():
            raise PermissionDenied("Permission denied")

        instance.is_active = False
        instance.save()
        
@extend_schema(request=LoginSerializer)
class CustomAuthToken(ObtainAuthToken):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        login_value = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=login_value, password=password)

        if user is None:
            try:
                db_user = User.objects.get(email=login_value, is_active=True)
                user = authenticate(
                    username=db_user.username,
                    password=password
                )
            except User.DoesNotExist:
                pass

        if user is None:
            return Response(
                {"error": "Invalid credentials"},
                status=status.HTTP_400_BAD_REQUEST
            )

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key
        })
        