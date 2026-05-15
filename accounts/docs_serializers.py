from rest_framework import serializers

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()

class AssignReportingSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    reporting_to_id = serializers.IntegerField()