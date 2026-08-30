from django.contrib import admin

from apps.platform.models import AuditEvent, IdempotencyKey, OutboxEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ["action", "entity_type", "entity_id", "actor_user", "occurred_at"]
    list_filter = ["entity_type", "action"]
    search_fields = ["entity_type", "action", "correlation_id", "request_id"]
    readonly_fields = [f.name for f in AuditEvent._meta.fields]

    def has_change_permission(self, request, obj=None):
        # طبق ZRV-ERD-002: Audit Append-Only است؛ حتی از پنل Admin هم
        # نباید قابل ویرایش باشد.
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OutboxEvent)
class OutboxEventAdmin(admin.ModelAdmin):
    list_display = [
        "event_type",
        "aggregate_type",
        "status",
        "attempt_count",
        "occurred_at",
    ]
    list_filter = ["status", "event_type"]
    readonly_fields = ["id", "occurred_at"]


@admin.register(IdempotencyKey)
class IdempotencyKeyAdmin(admin.ModelAdmin):
    list_display = ["key", "scope", "status", "created_at", "expires_at"]
    list_filter = ["status", "scope"]
    readonly_fields = ["key", "created_at"]
