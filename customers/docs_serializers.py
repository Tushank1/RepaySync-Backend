from rest_framework import serializers

class AssignCustomerSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    officer_id = serializers.IntegerField()

class BulkAssignCustomerSerializer(serializers.Serializer):
    customer_ids = serializers.ListField(
        child=serializers.IntegerField()
    )
    officer_id = serializers.IntegerField()