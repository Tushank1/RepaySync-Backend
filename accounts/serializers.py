from rest_framework import serializers
from .models import User, AuditLog
from .email_utils import generate_password, send_user_credentials

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        # fields = "__all__"
        exclude = ["password", "last_login", "is_superuser", "is_staff", "date_joined", "groups", "user_permissions"]
        read_only_fields = ["is_active"]

    
    def create(self, validated_data):
        raw_password = generate_password()
        print(f"Password for new user: {raw_password}")
        user = User(**validated_data)
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
                print(f"Failed to send email to {user.email}: {str(e)}")
                
        return user
    
class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = "__all__"