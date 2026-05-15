import csv
from io import TextIOWrapper
from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .models import Interaction
from customers.models import Customer
from accounts.audit import create_audit_log
from drf_spectacular.utils import extend_schema

@extend_schema(
    request={
        "multipart/form-data": {
            "type": "object",
            "properties": {
                "file": {
                    "type": "string",
                    "format": "binary"
                }
            }
        }
    }
)
class InteractionCSVUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get_team_type(self, user):
        return "calling" if user.role == "calling_agent" else "field"

    def can_access_customer(self, uploader, customer):
        assigned_to = customer.assigned_to

        if uploader.role in ["admin", "calling_agent"]:
            return True

        if not assigned_to:
            return False

        if uploader.role == "collection_officer":
            return assigned_to == uploader

        if uploader.role == "manager":
            return assigned_to.manager == uploader

        if uploader.role == "super_manager":
            return (
                assigned_to.manager and
                assigned_to.manager.manager == uploader
            )

        return False

    def post(self, request):
        user = request.user

        file = request.FILES.get("file")
        if not file:
            return Response(
                {"error": "CSV file is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        reader = csv.DictReader(TextIOWrapper(file.file, encoding="utf-8"))

        created_count = 0
        failed_rows = []
        team = self.get_team_type(user)

        for index, row in enumerate(reader, start=1):

            # -----------------------------
            # CUSTOMER LOOKUP
            # -----------------------------
            customer_email = row.get("customer_email")

            if not customer_email:
                failed_rows.append({
                    "row": index,
                    "reason": "customer_email missing",
                    "data": row
                })
                continue

            try:
                customer = Customer.objects.get(
                    email=customer_email,
                    is_active=True
                )
            except Customer.DoesNotExist:
                failed_rows.append({
                    "row": index,
                    "reason": "Customer not found",
                    "data": row
                })
                continue

            # -----------------------------
            # HIERARCHY CHECK
            # -----------------------------
            if not self.can_access_customer(user, customer):
                failed_rows.append({
                    "row": index,
                    "reason": "Customer not in your hierarchy",
                    "data": row
                })
                continue

            # -----------------------------
            # DATE CONVERSION
            # CSV format => 5/17/2026
            # DB format  => 2026-05-17
            # -----------------------------
            next_call_date = None
            raw_date = row.get("next_call_date")

            if raw_date:
                try:
                    next_call_date = datetime.strptime(
                        raw_date.strip(),
                        "%m/%d/%Y"
                    ).date()
                except ValueError:
                    failed_rows.append({
                        "row": index,
                        "reason": "Invalid date format. Use MM/DD/YYYY",
                        "data": row
                    })
                    continue

            # -----------------------------
            # CREATE INTERACTION
            # -----------------------------
            try:
                Interaction.objects.create(
                    customer=customer,
                    updated_by=user,
                    team=team,
                    comment=row.get("comment"),
                    disposition=row.get("disposition"),
                    next_call_date=next_call_date
                )

                created_count += 1

            except Exception as e:
                failed_rows.append({
                    "row": index,
                    "reason": str(e),
                    "data": row
                })

        # -----------------------------
        # AUDIT LOG
        # -----------------------------
        create_audit_log(
            user,
            "bulk uploaded interactions",
            f"{created_count} success, {len(failed_rows)} failed"
        )

        return Response({
            "message": "Interaction CSV processed successfully",
            "created_count": created_count,
            "failed_count": len(failed_rows),
            "failed_rows": failed_rows[:50]
        }, status=status.HTTP_200_OK)