from .models import AuditLog

def create_audit_log(user, action, target):
    AuditLog.objects.create(
        user=user,
        action=action,
        target=target
    )