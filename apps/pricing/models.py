"""
Pricing App

مرجع: ZRV-ERD-002 بخش ۵.۲ تا ۵.۴ (دامنه قیمت‌گذاری)

اصول کلیدی:
  - Market Quote یک Observation است؛ هرگز مستقیماً قیمت توافقی معامله
    را تعیین نمی‌کند (طبق ADR-012).
  - هر طلافروشی می‌تواند برای هر AssetType اجرت/سود اختصاصی خودش را
    تنظیم کند (طبق ZRV-FLOW-001 بخش ۳).
  - فقط یک تنظیم اجرت هم‌زمان برای هر (طلافروشی، نوع دارایی) فعال است؛
    تغییر اجرت رکورد قبلی را می‌بندد و رکورد جدید می‌سازد - نه Overwrite.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.tenancy.models import OrganizationType


class ProviderStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    INACTIVE = "INACTIVE", "غیرفعال"


class PricingProvider(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۵.۲ / جدول `pricing_providers`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=100)
    priority = models.PositiveSmallIntegerField(default=100)
    status = models.CharField(
        max_length=16, choices=ProviderStatus.choices, default=ProviderStatus.ACTIVE
    )

    class Meta:
        app_label = "pricing"
        db_table = "pricing_providers"
        ordering = ["priority"]

    def __str__(self):
        return self.name


class QuoteQualityStatus(models.TextChoices):
    VALID = "VALID", "معتبر"
    STALE = "STALE", "قدیمی"
    REJECTED = "REJECTED", "رد شده"


class MarketQuote(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۵.۳ / جدول `market_quotes`

    Observation است، نه قیمت توافقی معامله (ADR-012). price_per_mesghal
    مقدار مشتق‌شده برای نمایش است؛ محاسبه‌اش باید همیشه از طریق
    common.constants.gram_to_mesghal_price انجام شود - نه دستی و پراکنده.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        "pricing.PricingProvider", on_delete=models.PROTECT, related_name="quotes"
    )
    asset_type = models.ForeignKey(
        "catalog.AssetType", on_delete=models.PROTECT, related_name="quotes"
    )
    price_per_gram = models.DecimalField(max_digits=18, decimal_places=2)
    price_per_mesghal = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=3, default="IRR")
    observed_at = models.DateTimeField()
    received_at = models.DateTimeField(auto_now_add=True)
    quality_status = models.CharField(
        max_length=16,
        choices=QuoteQualityStatus.choices,
        default=QuoteQualityStatus.VALID,
    )

    class Meta:
        app_label = "pricing"
        db_table = "market_quotes"
        indexes = [models.Index(fields=["asset_type", "-observed_at"])]
        ordering = ["-observed_at"]

    def __str__(self):
        return f"{self.asset_type.code}={self.price_per_gram}/g @ {self.observed_at}"


class LaborFeeType(models.TextChoices):
    PERCENTAGE = "PERCENTAGE", "درصدی"
    FIXED_PER_GRAM = "FIXED_PER_GRAM", "ثابت به‌ازای هر گرم"


class RetailerProductPricing(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۵.۴ / جدول `retailer_product_pricing`

    فقط یک تنظیم فعال هم‌زمان به‌ازای هر (organization, asset_type)
    مجاز است (Partial Unique Index روی effective_to IS NULL) - دقیقاً
    همان نمونه کد مرجع در ZRV-ENG-002 بخش ۶.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="product_pricings",
    )
    asset_type = models.ForeignKey(
        "catalog.AssetType",
        on_delete=models.PROTECT,
        related_name="retailer_pricings",
    )
    labor_fee_type = models.CharField(max_length=20, choices=LaborFeeType.choices)
    labor_fee_value = models.DecimalField(max_digits=14, decimal_places=4)
    profit_margin_percentage = models.DecimalField(
        max_digits=6, decimal_places=3, null=True, blank=True
    )
    effective_from = models.DateTimeField()
    effective_to = models.DateTimeField(null=True, blank=True)
    created_by_membership = models.ForeignKey(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        related_name="created_pricings",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "pricing"
        db_table = "retailer_product_pricing"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "asset_type"],
                condition=models.Q(effective_to__isnull=True),
                name="uniq_active_pricing_per_org_asset",
            ),
        ]
        indexes = [models.Index(fields=["organization", "asset_type"])]

    def __str__(self):
        return f"{self.organization.display_name} / {self.asset_type.code}"

    def clean(self):
        """
        مرجع: ZRV-FLOW-001 - فقط طلافروشی (نه بنکدار، نه طلاساز) اجرت
        اختصاصی تنظیم می‌کند. Membership ثبت‌کننده هم باید متعلق به همان
        Organization باشد (نه یک کارمند سازمان دیگر).

        طبق اصل «Business Logic در save() ممنوع»، این Validation باید
        توسط Application Service آینده با full_clean() فراخوانی شود.
        """
        if self.organization.organization_type != OrganizationType.RETAILER:
            raise ValidationError(
                "فقط سازمان از نوع RETAILER می‌تواند اجرت محصول تنظیم کند."
            )
        if self.created_by_membership.organization_id != self.organization_id:
            raise ValidationError(
                "Membership ثبت‌کننده باید متعلق به همان طلافروشی باشد."
            )
