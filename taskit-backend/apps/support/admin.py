from django.contrib import admin

from .models import SupportConversation, SupportMessage, SupportTicket


class SupportMessageInline(admin.TabularInline):
    model = SupportMessage
    extra = 0
    readonly_fields = ("sender", "content", "created_at")
    can_delete = False


@admin.register(SupportConversation)
class SupportConversationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "created_at", "updated_at")
    search_fields = ("user__email", "user__full_name", "title", "messages__content")
    readonly_fields = ("created_at", "updated_at")
    inlines = [SupportMessageInline]


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "created_at")
    list_filter = ("sender", "created_at")
    search_fields = ("conversation__user__email", "content")
    readonly_fields = ("created_at",)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "status", "priority", "created_at", "updated_at")
    list_filter = ("status", "priority", "created_at")
    search_fields = ("title", "description", "user__email", "user__full_name", "admin_notes")
    readonly_fields = ("created_at", "updated_at")
