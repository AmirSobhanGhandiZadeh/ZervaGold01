from django.contrib import admin

from apps.consumer.models import (
    AutoApprovalPolicy,
    BuyerOrder,
    InternalInvoice,
    OrderReservation,
)


class OrderReservationInline(admin.StackedInline):
    model = OrderReservation
    extra = 0


class InternalInvoiceInline(admin.StackedInline):
    model = InternalInvoice
    extra = 0


@admin.register(BuyerOrder)
class BuyerOrderAdmin(admin.ModelAdmin):
    list_display = [
        "gold_account",
        "organization",
        "direction",
        "computed_grams",
        "status",
        "kyc_check_result",
        "created_at",
    ]
    list_filter = ["direction", "status", "kyc_check_result"]
    search_fields = ["gold_account__user__mobile_e164", "organization__display_name"]
    readonly_fields = ["id", "created_at"]
    inlines = [OrderReservationInline, InternalInvoiceInline]


@admin.register(OrderReservation)
class OrderReservationAdmin(admin.ModelAdmin):
    list_display = ["buyer_order", "reserved_grams", "status", "expires_at"]
    list_filter = ["status"]


@admin.register(AutoApprovalPolicy)
class AutoApprovalPolicyAdmin(admin.ModelAdmin):
    list_display = [
        "organization",
        "max_auto_approve_grams",
        "price_tolerance_percentage",
        "is_active",
    ]


@admin.register(InternalInvoice)
class InternalInvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "organization",
        "grams",
        "amount_toman",
        "issued_at",
        "is_fiscal_authority_submitted",
    ]
    search_fields = ["invoice_number"]
