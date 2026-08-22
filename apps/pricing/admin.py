from django.contrib import admin

from apps.pricing.models import MarketQuote, PricingProvider, RetailerProductPricing


@admin.register(PricingProvider)
class PricingProviderAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "priority", "status"]
    list_filter = ["status"]


@admin.register(MarketQuote)
class MarketQuoteAdmin(admin.ModelAdmin):
    list_display = [
        "asset_type",
        "provider",
        "price_per_gram",
        "price_per_mesghal",
        "quality_status",
        "observed_at",
    ]
    list_filter = ["asset_type", "provider", "quality_status"]
    readonly_fields = ["id", "received_at"]


@admin.register(RetailerProductPricing)
class RetailerProductPricingAdmin(admin.ModelAdmin):
    list_display = [
        "organization",
        "asset_type",
        "labor_fee_type",
        "labor_fee_value",
        "effective_from",
        "effective_to",
    ]
    list_filter = ["labor_fee_type", "asset_type"]
    search_fields = ["organization__display_name"]
    readonly_fields = ["id", "created_at"]
