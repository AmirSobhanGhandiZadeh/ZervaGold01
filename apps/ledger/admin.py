from django.contrib import admin

from apps.ledger.models import (
    GoldAccount,
    GoldAccountRetailerPosition,
    GoldLedgerLine,
    GoldLedgerTransaction,
)


@admin.register(GoldAccount)
class GoldAccountAdmin(admin.ModelAdmin):
    list_display = ["user", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__mobile_e164"]
    readonly_fields = ["id", "created_at"]


@admin.register(GoldAccountRetailerPosition)
class GoldAccountRetailerPositionAdmin(admin.ModelAdmin):
    list_display = [
        "gold_account",
        "organization",
        "asset_type",
        "balance_grams",
        "available_grams",
        "reserved_grams",
    ]
    list_filter = ["organization", "asset_type"]
    readonly_fields = ["id", "updated_at"]


class GoldLedgerLineInline(admin.TabularInline):
    model = GoldLedgerLine
    extra = 0
    readonly_fields = ["id", "created_at"]


@admin.register(GoldLedgerTransaction)
class GoldLedgerTransactionAdmin(admin.ModelAdmin):
    list_display = ["transaction_type", "occurred_at", "idempotency_key"]
    list_filter = ["transaction_type"]
    readonly_fields = ["id", "created_at"]
    inlines = [GoldLedgerLineInline]
