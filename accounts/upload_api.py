import csv
from io import TextIOWrapper
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from .models import User
from drf_spectacular.utils import extend_schema
from .email_utils import generate_password, send_user_credentials

@extend_schema(
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "file": {"type": "string", "format": "binary"}
            }
        }
    }
)
class UserCSVUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def validate_role_permission(self, uploader, role):
        if uploader.role == "admin":
            return True

        if uploader.role == "super_manager":
            return role in ["manager", "collection_officer"]

        if uploader.role == "manager":
            return role == "collection_officer"

        return False

    def post(self, request):
        uploader = request.user

        if uploader.role in ["calling_agent", "collection_officer"]:
            raise PermissionDenied("You are not allowed to upload CSV")

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "CSV file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        rows = list(csv.DictReader(TextIOWrapper(file.file, encoding="utf-8")))

        failed_rows = []

        # ------------------------------------
        # STAGE 1: GROUP ROWS BY ROLE
        # ------------------------------------
        super_managers = []
        managers = []
        officers = []

        for index, row in enumerate(rows, start=1):
            role = row.get("role")

            if not self.validate_role_permission(uploader, role):
                failed_rows.append({
                    "row": index,
                    "reason": f"{uploader.role} cannot create {role}",
                    "data": row
                })
                continue

            row["_index"] = index  # keep track

            if role == "super_manager":
                super_managers.append(row)
            elif role == "manager":
                managers.append(row)
            elif role == "collection_officer":
                officers.append(row)
            else:
                failed_rows.append({
                    "row": index,
                    "reason": "Invalid role",
                    "data": row
                })

        created_users = []

        # ------------------------------------
        # STAGE 2: CREATE SUPER MANAGERS
        # ------------------------------------
        super_manager_map = {}

        for row in super_managers:
            user = User(
                username=row["username"],
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                email=row["email"],
                role="super_manager",
                phone=row.get("phone"),
                manager=uploader if uploader.role == "admin" else None
            )
            raw_password = generate_password()
            user.set_password(raw_password)
            user.save()
            
            if user.email:
                try:
                    send_user_credentials(
                        user.email,
                        user.username,
                        raw_password
                    )
                except Exception as e:
                    pass

            super_manager_map[user.username] = user
            created_users.append(user)

        # ------------------------------------
        # STAGE 3: CREATE MANAGERS
        # ------------------------------------
        manager_map = {}

        for row in managers:
            manager = uploader

            # optional admin override
            if uploader.role == "admin":
                manager_username = row.get("manager_username")
                if manager_username:
                    try:
                        manager = User.objects.get(username=manager_username)
                    except User.DoesNotExist:
                        failed_rows.append({
                            "row": row["_index"],
                            "reason": "Manager not found",
                            "data": row
                        })
                        continue

            user = User(
                username=row["username"],
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                email=row["email"],
                role="manager",
                phone=row.get("phone"),
                manager=manager
            )
            raw_password = generate_password()
            user.set_password(raw_password)
            user.save()
            
            if user.email:
                try:
                    send_user_credentials(
                        user.email,
                        user.username,
                        raw_password
                    )
                except Exception as e:
                    pass

            manager_map[user.username] = user
            created_users.append(user)

        # ------------------------------------
        # STAGE 4: CREATE COLLECTION OFFICERS
        # ------------------------------------
        for row in officers:

            manager = None

            if uploader.role == "manager":
                manager = uploader

            elif uploader.role == "super_manager":
                manager_username = row.get("manager_username")

                if not manager_username:
                    failed_rows.append({
                        "row": row["_index"],
                        "reason": "manager_username required",
                        "data": row
                    })
                    continue

                manager = manager_map.get(manager_username)

                if not manager:
                    failed_rows.append({
                        "row": row["_index"],
                        "reason": "Manager not found (must be created in same upload)",
                        "data": row
                    })
                    continue

                if manager.manager != uploader:
                    failed_rows.append({
                        "row": row["_index"],
                        "reason": "Manager not under this super manager",
                        "data": row
                    })
                    continue

            elif uploader.role == "admin":
                manager_username = row.get("manager_username")

                if manager_username:
                    manager = User.objects.filter(username=manager_username).first()

            user = User(
                username=row["username"],
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                email=row["email"],
                role="collection_officer",
                phone=row.get("phone"),
                manager=manager
            )
            raw_password = generate_password()
            user.set_password(raw_password)
            user.save()
            
            if user.email:
                try:
                    send_user_credentials(
                        user.email,
                        user.username,
                        raw_password
                    )
                except Exception as e:
                    pass

            created_users.append(user)

        # ------------------------------------
        # RESPONSE
        # ------------------------------------
        return Response({
            "message": "Users uploaded successfully",
            "created_count": len(created_users),
            "failed_count": len(failed_rows),
            "failed_rows": failed_rows[:50]
        }, status=status.HTTP_200_OK)