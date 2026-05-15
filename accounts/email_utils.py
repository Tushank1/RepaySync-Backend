import secrets
import string
from django.core.mail import send_mail

def generate_password(length=10):
    chars = string.ascii_letters + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def send_user_credentials(email, username, password):
    subject = "Your ReplaySync Account Credentials"

    message = f"""
Hello,

Your account has been created successfully.

Username: {username}
Password: {password}

Please login and change your password after first login.
"""

    send_mail(
        subject,
        message,
        None,
        [email],
        fail_silently=False,
    )