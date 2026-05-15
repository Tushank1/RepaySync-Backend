from django.db import models
from accounts.models import User
from customers.models import Customer

class Interaction(models.Model):
    TEAM_CHOICES = (
        ("field", "Field Team"),
        ("calling", "Calling Team"),
    )
    
    DISPOSITION_CHOICES = (
        ("paid", "Paid"),
        ("promise_to_pay", "Promise To Pay"),
        ("not_reachable", "Not Reachable"),
        ("refused", "Refused"),
        ("visited_home", "Visited Home"),
        ("callback_requested", "Callback Requested"),
    )

    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="interactions"
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    team = models.CharField(max_length=20, choices=TEAM_CHOICES)

    comment = models.TextField()

    disposition = models.CharField(
        max_length=50,
        choices=DISPOSITION_CHOICES
    )

    next_call_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        Customer.objects.filter(id=self.customer_id).update(
            latest_disposition=self.disposition
        )

    def __str__(self):
        return f"{self.customer.name} - {self.disposition}"