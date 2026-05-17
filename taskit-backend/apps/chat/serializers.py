from rest_framework import serializers

from .models import ChatThread, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.full_name", read_only=True)
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    image_url = serializers.SerializerMethodField()
    voice_note_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = (
            "id",
            "thread",
            "sender",
            "sender_name",
            "sender_email",
            "content",
            "image",
            "image_url",
            "voice_note",
            "voice_note_url",
            "timestamp",
            "is_read",
        )
        read_only_fields = (
            "id",
            "thread",
            "sender",
            "sender_name",
            "sender_email",
            "image_url",
            "voice_note_url",
            "timestamp",
            "is_read",
        )
        extra_kwargs = {
            "image": {"write_only": True, "required": False},
            "voice_note": {"write_only": True, "required": False},
            "content": {"required": False, "allow_blank": True},
        }

    def get_image_url(self, obj):
        if not obj.image:
            return ""
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

    def get_voice_note_url(self, obj):
        if not obj.voice_note:
            return ""
        request = self.context.get("request")
        url = obj.voice_note.url
        return request.build_absolute_uri(url) if request else url

    def validate(self, attrs):
        content = attrs.get("content", "")
        if not content.strip() and not attrs.get("image") and not attrs.get("voice_note"):
            raise serializers.ValidationError("Add a message, image, or voice note.")
        return attrs


class ChatThreadSerializer(serializers.ModelSerializer):
    task_id = serializers.IntegerField(source="task.id", read_only=True)
    task_title = serializers.CharField(source="task.title", read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ("id", "task_id", "task_title", "created_at", "last_message")
        read_only_fields = fields

    def get_last_message(self, obj):
        message = getattr(obj, "last_message_obj", None) or obj.messages.last()
        if message is None:
            return None
        return {
            "id": message.id,
            "sender_name": message.sender.full_name,
            "content": message.content,
            "timestamp": message.timestamp,
            "is_read": message.is_read,
        }
