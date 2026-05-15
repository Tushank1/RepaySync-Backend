import csv
from io import TextIOWrapper
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework import status
from .models import Customer
from accounts.models import User
from accounts.audit import create_audit_log
from drf_spectacular.utils import extend_schema

@extend_schema(
    request={"multipart/form-data": {"type": "object", "properties": {
        "file": {"type": "string", "format": "binary"}
    }}}
)
class CustomerCSVUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    # -----------------------------
    # Resolve officer safely
    # -----------------------------
    def resolve_officer(self, row, user):
        username = row.get("assigned_to_username")
        email = row.get("assigned_to_email")

        if not username and not email:
            return None, "Missing assigned_to_username or assigned_to_email"

        try:
            if username:
                officer = User.objects.get(username=username, is_active=True)
            else:
                officer = User.objects.get(email=email, is_active=True)

        except User.DoesNotExist:
            return None, "Collection officer not found"

        if officer.role != "collection_officer":
            return None, "User is not a collection officer"

        # -------------------------
        # Hierarchy validation
        # -------------------------
        if user.role == "manager":
            if officer.manager != user:
                return None, "Officer not in your team"

        if user.role == "super_manager":
            if (
                officer.manager is None or
                officer.manager.manager != user
            ):
                return None, "Officer not in your hierarchy"

        return officer, None

    # -----------------------------
    # Upload API
    # -----------------------------
    def post(self, request):
        user = request.user
        file = request.FILES.get("file")

        # ❌ Role check
        if user.role == "calling_agent":
            raise PermissionDenied("You are not allowed to upload CSV")

        if not file:
            return Response(
                {"error": "CSV file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        decoded_file = TextIOWrapper(file.file, encoding="utf-8")
        reader = csv.DictReader(decoded_file)

        created_count = 0
        failed_rows = []

        for index, row in enumerate(reader, start=1):

            assigned_to = None

            # -----------------------------
            # CASE 1: Collection Officer
            # -----------------------------
            if user.role == "collection_officer":
                assigned_to = user

            # -----------------------------
            # CASE 2: Admin (no assignment)
            # -----------------------------
            elif user.role == "admin":
                assigned_to = None

            # -----------------------------
            # CASE 3: Manager / Super Admin
            # -----------------------------
            elif user.role in ["manager", "super_manager"]:
                assigned_to, error = self.resolve_officer(row, user)

                if error:
                    failed_rows.append({
                        "row": index,
                        "reason": error,
                        "data": row
                    })
                    continue

            else:
                failed_rows.append({
                    "row": index,
                    "reason": "Invalid role",
                    "data": row
                })
                continue

            # -----------------------------
            # Create customer safely
            # -----------------------------
            try:
                Customer.objects.create(
                    name=row.get("name"),
                    phone=row.get("phone"),
                    email=row.get("email"),
                    address=row.get("address"),
                    assigned_to=assigned_to
                )
                created_count += 1

            except Exception as e:
                failed_rows.append({
                    "row": index,
                    "reason": str(e),
                    "data": row
                })

        # -----------------------------
        # Audit log
        # -----------------------------
        create_audit_log(
            user,
            "uploaded customer csv",
            f"{created_count} created, {len(failed_rows)} failed"
        )

        return Response({
            "message": "CSV processed successfully",
            "created_count": created_count,
            "failed_count": len(failed_rows),
            "failed_rows": failed_rows[:50]
        }, status=status.HTTP_200_OK)