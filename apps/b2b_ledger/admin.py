from django.contrib import admin

from apps.b2b_ledger.models import (
    DealerRetailerAccount,
    DealerRetailerLedgerEntry,
    WorkshopPurchaseRequest,
)


class DealerRetailerLedgerEntryInline(admin.TabularInline):
    model = DealerRetailerLedgerEntry
    extra = 0
    readonly_fields = ["id", "created_at"]


@admin.register(DealerRetailerAccount)
class DealerRetailerAccountAdmin(admin.ModelAdmin):
    list_display = ["bullion_dealer_org", "retailer_org", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["bullion_dealer_org__display_name", "retailer_org__display_name"]
    readonly_fields = ["id", "created_at"]
    inlines = [DealerRetailerLedgerEntryInline]


@admin.register(DealerRetailerLedgerEntry)
class DealerRetailerLedgerEntryAdmin(admin.ModelAdmin):
    list_display = ["account", "entry_type", "grams", "amount_toman", "occurred_at"]
    list_filter = ["entry_type"]
    readonly_fields = ["id", "created_at"]


@admin.register(WorkshopPurchaseRequest)
class WorkshopPurchaseRequestAdmin(admin.ModelAdmin):
    list_display = [
        "bullion_dealer_org",
        "workshop_org",
        "requested_grams",
        "delivery_status",
        "payment_status",
        "requested_at",
    ]
    list_filter = ["delivery_status", "payment_status"]
    readonly_fields = ["id", "requested_at"]
