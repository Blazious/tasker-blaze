from django.contrib import admin

from .models import ChatThread, Message


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ("task", "created_at")
    search_fields = ("task__title", "participants__email", "participants__full_name")
    readonly_fields = ("created_at",)
    filter_horizontal = ("participants",)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = (
        "thread",
        "sender",
        "has_image",
        "has_voice_note",
        "timestamp",
        "is_read",
    )
    list_filter = ("is_read", "timestamp")
    search_fields = ("thread__task__title", "sender__email", "sender__full_name", "content")
    readonly_fields = ("timestamp",)

    def has_image(self, obj):
        return bool(obj.image)

    has_image.boolean = True

    def has_voice_note(self, obj):
        return bool(obj.voice_note)

    has_voice_note.boolean = True
