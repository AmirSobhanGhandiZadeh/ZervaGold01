from django.contrib import admin

from apps.catalog.models import AssetType


@admin.register(AssetType)
class AssetTypeAdmin(admin.ModelAdmin):
    list_display = ["code", "display_name_fa", "purity", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "display_name_fa"]
    readonly_fields = ["id", "created_at"]
