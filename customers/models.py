from django.db import models
from accounts.models import User

class Customer(models.Model):
    DISPOSITION_CHOICES = (
        ("paid", "Paid"),
        ("promise_to_pay", "Promise To Pay"),
        ("not_reachable", "Not Reachable"),
        ("refused", "Refused"),
        ("visited_home", "Visited Home"),
        ("callback_requested", "Callback Requested"),
    )

    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    latest_disposition = models.CharField(
        max_length=50,
        choices=DISPOSITION_CHOICES,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_customers"
    )

    def __str__(self):
        return self.name