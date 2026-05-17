from rest_framework import serializers

from .models import SupportConversation, SupportMessage, SupportTicket


class SupportMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportMessage
        fields = ("id", "sender", "content", "created_at")
        read_only_fields = fields


class SupportConversationSerializer(serializers.ModelSerializer):
    messages = SupportMessageSerializer(many=True, read_only=True)

    class Meta:
        model = SupportConversation
        fields = ("id", "title", "created_at", "updated_at", "messages")
        read_only_fields = fields


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = (
            "id",
            "title",
            "description",
            "status",
            "priority",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SupportChatRequestSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    conversation_id = serializers.IntegerField(required=False)

    def validate_message(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError("Message is too short.")
        return value


class SupportEscalationSerializer(serializers.Serializer):
    conversation_id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=160)
    description = serializers.CharField(max_length=2000)
    priority = serializers.ChoiceField(
        choices=SupportTicket.Priority.choices,
        default=SupportTicket.Priority.NORMAL,
    )
