from django.contrib import admin

from apps.inventory.models import InventoryPosition


@admin.register(InventoryPosition)
class InventoryPositionAdmin(admin.ModelAdmin):
    list_display = [
        "organization",
        "asset_type",
        "available_grams",
        "reserved_grams",
        "last_synced_from_rfid_at",
        "updated_at",
    ]
    list_filter = ["asset_type"]
    search_fields = ["organization__display_name"]
    readonly_fields = ["id", "updated_at"]
