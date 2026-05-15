from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework import status
from drf_spectacular.utils import extend_schema
from .models import User
from .email_utils import generate_password, send_user_credentials
from rest_framework import serializers

class ChangePasswordRequestSerializer(serializers.Serializer):
    old_password = serializers.CharField()
    new_password = serializers.CharField()
    
class ForgetPasswordRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

@extend_schema(request=ChangePasswordRequestSerializer)
class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        old_password = request.data.get("old_password")
        new_password = request.data.get("new_password")

        if not old_password or not new_password:
            raise ValidationError(
                "old_password and new_password are required"
            )

        user = request.user

        if not user.check_password(old_password):
            return Response(
                {"error": "Old password is incorrect"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        return Response({
            "message": "Password changed successfully"
        })
        
@extend_schema(request=ForgetPasswordRequestSerializer)
class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email")

        if not email:
            raise ValidationError("email is required")

        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        new_password = generate_password()

        user.set_password(new_password)
        user.save()

        try:
            send_user_credentials(
                user.email,
                user.username,
                new_password
            )
        except Exception:
            pass

        return Response({
            "message": "New password sent to email"
        })