from rest_framework import serializers

from content.models import ContactMessage


class StaffContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            "id",
            "name",
            "email",
            "phone",
            "subject",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["name", "email", "phone", "subject", "message", "created_at"]
