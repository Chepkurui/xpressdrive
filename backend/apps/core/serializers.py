from rest_framework import serializers

from apps.data.models import ContactMessage
from .validators import phone_validator


class ContactMessageSerializer(serializers.ModelSerializer):
    # Honeypot: real users never see or fill this field.
    website = serializers.CharField(required=False, allow_blank=True, write_only=True, max_length=200)
    phone = serializers.CharField(required=False, allow_blank=True, validators=[phone_validator])

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "message", "website"]

    def create(self, validated_data):
        validated_data.pop("website", None)
        return super().create(validated_data)
