# api/serializers.py
from rest_framework import serializers

class DataSerializer(serializers.Serializer):
    addressId = serializers.IntegerField()
    latitude = serializers.CharField()
    longitude = serializers.CharField()

class RequestGeoreferenceSerializer(serializers.Serializer):
    countyName = serializers.CharField(max_length=100)
    streetName = serializers.CharField(max_length=100)
    number = serializers.CharField(max_length=100)

class ResponseGeoreferenceSerializer(serializers.Serializer):
    data = DataSerializer()
    statusCode = serializers.IntegerField(required=False)
    statusDescription = serializers.CharField(required=False)
    errors = serializers.ListField(child=serializers.CharField(), required=False)