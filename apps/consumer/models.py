"""
Consumer App — سفارش خرید/فروش خریدار

مرجع: ZRV-ERD-002 بخش ۸ (دامنه سفارش خرید/فروش خریدار)

قوانین کلیدی طبق ZRV-FLOW-001:
  - خرید همیشه باید یک طلافروشی مشخص را هدف بگیرد؛ مسیر «خرید مستقیم از
    زروا» (بدون Retailer) در این Commit اصلاً وجود ندارد تا فعال شود.
  - فروش خریدار همیشه باید همان Retailer Position را که ازش خریده هدف
    بگیرد - این قانون توسط OrderReservation.clean() enforce می‌شود.
  - در MVP0 فرمول دقیق تایید خودکار هنوز TBD است (به AutoApprovalPolicy
    مراجعه شود)؛ مکانیزم پرداخت درون‌برنامه‌ای هم به Application Service
    آینده موکول شده - این جدول‌ها فقط رکورد را نگه می‌دارند، نه Integration
    واقعی با درگاه پرداخت.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.tenancy.models import OrganizationType


class OrderDirection(models.TextChoices):
    BUY = "BUY", "خرید"
    SELL = "SELL", "فروش"


class OrderInputMode(models.TextChoices):
    TOMAN_TO_GRAM = "TOMAN_TO_GRAM", "ریال به گرم"
    GRAM_TO_TOMAN = "GRAM_TO_TOMAN", "گرم به ریال"


class KycCheckResult(models.TextChoices):
    PASSED = "PASSED", "قبول"
    FAILED_LIMIT = "FAILED_LIMIT", "رد به‌دلیل سقف"


class OrderStatus(models.TextChoices):
    DRAFT = "DRAFT", "پیش‌نویس"
    RESERVED = "RESERVED", "رزرو شده"
    AUTO_APPROVED = "AUTO_APPROVED", "تایید خودکار"
    REJECTED = "REJECTED", "رد شده"
    EXPIRED = "EXPIRED", "منقضی شده"
    COMPLETED = "COMPLETED", "تکمیل شده"


class BuyerOrder(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۸.۱ / جدول `buyer_orders`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gold_account = models.ForeignKey(
        "ledger.GoldAccount", on_delete=models.PROTECT, related_name="orders"
    )
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="buyer_orders"
    )
    asset_type = models.ForeignKey(
        "catalog.AssetType", on_delete=models.PROTECT, related_name="buyer_orders"
    )
    direction = models.CharField(max_length=4, choices=OrderDirection.choices)
    input_mode = models.CharField(max_length=20, choices=OrderInputMode.choices)
    requested_toman_amount = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    requested_grams = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    price_per_gram_snapshot = models.DecimalField(max_digits=18, decimal_places=2)
    computed_grams = models.DecimalField(max_digits=18, decimal_places=6)
    computed_toman_amount = models.DecimalField(max_digits=18, decimal_places=2)
    kyc_tier_at_request = models.PositiveSmallIntegerField()
    kyc_check_result = models.CharField(max_length=16, choices=KycCheckResult.choices)
    status = models.CharField(
        max_length=16, choices=OrderStatus.choices, default=OrderStatus.DRAFT
    )
    idempotency_key = models.CharField(max_length=100, unique=True)
    performed_by_membership = models.ForeignKey(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="handled_orders",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "consumer"
        db_table = "buyer_orders"
        indexes = [
            models.Index(fields=["organization", "-created_at"]),
            models.Index(fields=["gold_account", "-created_at"]),
        ]

    def __str__(self):
        org_name = self.organization.display_name
        return f"{self.direction} {self.computed_grams}g @ {org_name}"

    def clean(self):
        """
        طبق ZRV-FLOW-001: خرید مستقیم از زروا (بدون طلافروشی) در MVP0
        غیرفعال است - organization همیشه باید یک RETAILER معتبر باشد.

        طبق اصل «Business Logic در save() ممنوع»، این Validation باید
        توسط Application Service آینده با full_clean() فراخوانی شود.
        """
        if self.organization.organization_type != OrganizationType.RETAILER:
            raise ValidationError(
                "سفارش خریدار همیشه باید یک طلافروشی (RETAILER) مشخص را "
                "هدف بگیرد - خرید مستقیم از زروا در MVP0 غیرفعال است."
            )
        if not self.requested_toman_amount and not self.requested_grams:
            raise ValidationError(
                "حداقل یکی از requested_toman_amount یا requested_grams "
                "باید مقداردهی شود."
            )


class ReservationStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    RELEASED = "RELEASED", "آزادشده"
    CONVERTED = "CONVERTED", "تبدیل‌شده"


class OrderReservation(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۸.۲ / جدول `order_reservations`

    رزرو بلافاصله پس از ثبت سفارش ایجاد می‌شود - قبل از اجرای منطق
    تایید خودکار - تا از Double-Allocation جلوگیری شود.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer_order = models.OneToOneField(
        "consumer.BuyerOrder", on_delete=models.PROTECT, related_name="reservation"
    )
    inventory_position = models.ForeignKey(
        "inventory.InventoryPosition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_reservations",
    )
    gold_account_retailer_position = models.ForeignKey(
        "ledger.GoldAccountRetailerPosition",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="order_reservations",
    )
    reserved_grams = models.DecimalField(max_digits=18, decimal_places=6)
    status = models.CharField(
        max_length=16,
        choices=ReservationStatus.choices,
        default=ReservationStatus.ACTIVE,
    )
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "consumer"
        db_table = "order_reservations"

    def __str__(self):
        return f"Reservation({self.buyer_order_id}, {self.reserved_grams}g)"

    def clean(self):
        """
        قانون قفل فروش (طبق ZRV-ERD-002 بخش ۸.۱): برای SELL، Position
        هدف باید متعلق به همان Retailer باشد که BuyerOrder به آن اشاره
        می‌کند - این دقیقاً همان مکانیزم فنی است که خریدار را از فروش
        به یک طلافروشی دیگر منع می‌کند.
        """
        order = self.buyer_order

        if order.direction == OrderDirection.BUY:
            if self.inventory_position is None:
                raise ValidationError("سفارش خرید باید InventoryPosition رزرو کند.")
            if self.gold_account_retailer_position is not None:
                raise ValidationError(
                    "سفارش خرید نباید GoldAccountRetailerPosition رزرو کند."
                )
            if self.inventory_position.organization_id != order.organization_id:
                raise ValidationError(
                    "InventoryPosition رزروشده باید متعلق به همان طلافروشی سفارش باشد."
                )

        elif order.direction == OrderDirection.SELL:
            if self.gold_account_retailer_position is None:
                raise ValidationError(
                    "سفارش فروش باید GoldAccountRetailerPosition رزرو کند."
                )
            if self.inventory_position is not None:
                raise ValidationError("سفارش فروش نباید InventoryPosition رزرو کند.")
            if (
                self.gold_account_retailer_position.organization_id
                != order.organization_id
            ):
                raise ValidationError(
                    "خریدار فقط می‌تواند به همان طلافروشی که از آن خریده "
                    "بفروشد (قانون قفل فروش طبق ZRV-FLOW-001)."
                )


class AutoApprovalPolicy(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۸.۳ / جدول `auto_approval_policies`

    🧮 فرمول دقیق هنوز TBD است (به ZRV-FLOW-001 بخش ۹ مراجعه شود). در
    MVP0 عملاً همه سفارش‌ها Auto Approve می‌شوند تا فرمول واقعی طراحی
    شود؛ ساختار جدول از الان آماده است تا افزودن فرمول واقعی نیاز به
    Migration ساختاری نداشته باشد.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="auto_approval_policies",
    )
    max_auto_approve_grams = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    price_tolerance_percentage = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    price_growth_rate_threshold = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "consumer"
        db_table = "auto_approval_policies"

    def __str__(self):
        scope = self.organization.display_name if self.organization else "سراسری"
        return f"AutoApprovalPolicy({scope})"


class InternalInvoice(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۸.۴ / جدول `internal_invoices`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    buyer_order = models.OneToOneField(
        "consumer.BuyerOrder", on_delete=models.PROTECT, related_name="invoice"
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="issued_invoices",
    )
    gold_account = models.ForeignKey(
        "ledger.GoldAccount", on_delete=models.PROTECT, related_name="invoices"
    )
    grams = models.DecimalField(max_digits=18, decimal_places=6)
    amount_toman = models.DecimalField(max_digits=18, decimal_places=2)
    issued_at = models.DateTimeField()
    is_fiscal_authority_submitted = models.BooleanField(default=False)

    class Meta:
        app_label = "consumer"
        db_table = "internal_invoices"

    def __str__(self):
        return self.invoice_number
