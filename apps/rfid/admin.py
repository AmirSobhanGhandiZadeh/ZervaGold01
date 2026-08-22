from django.contrib import admin

from apps.rfid.models import RfidSyncEvent, RfidTag


@admin.register(RfidTag)
class RfidTagAdmin(admin.ModelAdmin):
    list_display = ["epc", "organization", "inventory_position", "status"]
    list_filter = ["status"]
    search_fields = ["epc"]


@admin.register(RfidSyncEvent)
class RfidSyncEventAdmin(admin.ModelAdmin):
    list_display = ["organization", "event_type", "occurred_at"]
    list_filter = ["event_type"]
    readonly_fields = ["id"]
