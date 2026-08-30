"""
B2B Ledger App

مرجع: ZRV-ERD-002 بخش ۹ و ۱۰ (حساب باز طلافروش↔بنکدار و درخواست
بنکدار↔طلاساز)

اصول کلیدی طبق ZRV-FLOW-001:
  - رابطه طلافروش↔بنکدار = حساب باز (نسیه)؛ هر جابجایی پول یا جنس یک
    رکورد جداست، نه Overwrite یک عدد Balance.
  - تسویه واقعی خارج از اپ انجام می‌شود؛ این جدول‌ها فقط رکورد را ثبت
    می‌کنند.
  - رابطه بنکدار↔طلاساز فقط شامل درخواست خرید + وضعیت تحویل/پرداخت
    است؛ بدون مذاکره قیمت.
  - بنکدار↔بنکدار خارج از اسکوپ فعلی است.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, DecimalField, Sum, When

from apps.tenancy.models import OrganizationType


class DealerRetailerAccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    SUSPENDED = "SUSPENDED", "معلق"


class DealerRetailerEntryType(models.TextChoices):
    GOLD_WITHDRAWAL = "GOLD_WITHDRAWAL", "برداشت جنس"
    SETTLEMENT_PAYMENT = "SETTLEMENT_PAYMENT", "تسویه"
    ADJUSTMENT = "ADJUSTMENT", "اصلاحیه"


class DealerRetailerAccount(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۹.۱ / جدول `dealer_retailer_accounts`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bullion_dealer_org = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="dealer_accounts",
    )
    retailer_org = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="retailer_accounts",
    )
    status = models.CharField(
        max_length=16,
        choices=DealerRetailerAccountStatus.choices,
        default=DealerRetailerAccountStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "b2b_ledger"
        db_table = "dealer_retailer_accounts"
        constraints = [
            models.UniqueConstraint(
                fields=["bullion_dealer_org", "retailer_org"],
                name="uniq_dealer_retailer_pair",
            ),
        ]

    def __str__(self):
        dealer = self.bullion_dealer_org.display_name
        retailer = self.retailer_org.display_name
        return f"{dealer} <-> {retailer}"

    def clean(self):
        """طبق ZRV-ERD-002: هر طرف باید نوع سازمانی درست داشته باشد."""
        if self.bullion_dealer_org.organization_type != OrganizationType.BULLION_DEALER:
            raise ValidationError("bullion_dealer_org باید از نوع BULLION_DEALER باشد.")
        if self.retailer_org.organization_type != OrganizationType.RETAILER:
            raise ValidationError("retailer_org باید از نوع RETAILER باشد.")

    def reconstruct_balance_toman(self):
        """
        مانده بدهی را مستقیماً از رکوردهای Ledger بازسازی می‌کند - دقیقاً
        طبق مصداق تایید‌شده در ZRV-ERD-002 بخش ۹.۲:

            مانده = Σ GOLD_WITHDRAWAL − Σ SETTLEMENT_PAYMENT + Σ ADJUSTMENT

        هرگز مستقیم ذخیره نمی‌شود؛ همیشه از این تابع محاسبه می‌شود.
        """
        aggregation = self.entries.aggregate(
            total=Sum(
                Case(
                    When(
                        entry_type=DealerRetailerEntryType.GOLD_WITHDRAWAL,
                        then=models.F("amount_toman"),
                    ),
                    When(
                        entry_type=DealerRetailerEntryType.SETTLEMENT_PAYMENT,
                        then=-models.F("amount_toman"),
                    ),
                    When(
                        entry_type=DealerRetailerEntryType.ADJUSTMENT,
                        then=models.F("amount_toman"),
                    ),
                    output_field=DecimalField(max_digits=18, decimal_places=2),
                )
            )
        )
        return aggregation["total"] or 0


class DealerRetailerLedgerEntry(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۹.۲ / جدول `dealer_retailer_ledger_entries`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey(
        "b2b_ledger.DealerRetailerAccount",
        on_delete=models.PROTECT,
        related_name="entries",
    )
    entry_type = models.CharField(
        max_length=20, choices=DealerRetailerEntryType.choices
    )
    grams = models.DecimalField(max_digits=18, decimal_places=6, null=True, blank=True)
    price_per_gram_at_transaction = models.DecimalField(
        max_digits=18, decimal_places=2, null=True, blank=True
    )
    amount_toman = models.DecimalField(max_digits=18, decimal_places=2)
    occurred_at = models.DateTimeField()
    recorded_by_membership = models.ForeignKey(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        related_name="recorded_dealer_entries",
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "b2b_ledger"
        db_table = "dealer_retailer_ledger_entries"
        indexes = [models.Index(fields=["account", "-occurred_at"])]

    def __str__(self):
        return f"{self.entry_type} {self.amount_toman} @ {self.occurred_at}"

    def clean(self):
        """
        مرجع: ZRV-ERD-002 بخش ۹.۲
          - grams و price_per_gram_at_transaction فقط برای
            GOLD_WITHDRAWAL معنادارند.
          - Membership ثبت‌کننده باید عضو یکی از دو طرف حساب باشد.
        """
        if self.entry_type == DealerRetailerEntryType.GOLD_WITHDRAWAL:
            if self.grams is None or self.price_per_gram_at_transaction is None:
                raise ValidationError(
                    "برای GOLD_WITHDRAWAL، grams و "
                    "price_per_gram_at_transaction الزامی‌اند."
                )
        elif self.grams is not None:
            raise ValidationError("grams فقط برای رکوردهای GOLD_WITHDRAWAL مجاز است.")

        valid_org_ids = {
            self.account.bullion_dealer_org_id,
            self.account.retailer_org_id,
        }
        if self.recorded_by_membership.organization_id not in valid_org_ids:
            raise ValidationError(
                "Membership ثبت‌کننده باید عضو یکی از دو طرف این حساب باشد."
            )


class WorkshopRequestDeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "در انتظار"
    DELIVERED = "DELIVERED", "تحویل شد"
    NOT_DELIVERED = "NOT_DELIVERED", "تحویل نشد"


class WorkshopRequestPaymentStatus(models.TextChoices):
    PENDING = "PENDING", "در انتظار"
    PAID = "PAID", "پرداخت شد"
    NOT_PAID = "NOT_PAID", "پرداخت نشد"


class WorkshopPurchaseRequest(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۱۰.۱ / جدول `workshop_purchase_requests`

    این رابطه عمداً ساده نگه داشته شده: فقط درخواست + وضعیت تحویل +
    وضعیت پرداخت - بدون مذاکره قیمت یا Negotiation Engine.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bullion_dealer_org = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="workshop_purchase_requests",
    )
    workshop_org = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="incoming_purchase_requests",
    )
    requested_grams = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    spec_notes = models.TextField(blank=True)
    delivery_status = models.CharField(
        max_length=16,
        choices=WorkshopRequestDeliveryStatus.choices,
        default=WorkshopRequestDeliveryStatus.PENDING,
    )
    payment_status = models.CharField(
        max_length=16,
        choices=WorkshopRequestPaymentStatus.choices,
        default=WorkshopRequestPaymentStatus.PENDING,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    delivery_updated_at = models.DateTimeField(null=True, blank=True)
    payment_updated_at = models.DateTimeField(null=True, blank=True)
    recorded_by_membership = models.ForeignKey(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_workshop_requests",
    )

    class Meta:
        app_label = "b2b_ledger"
        db_table = "workshop_purchase_requests"
        indexes = [models.Index(fields=["workshop_org", "-requested_at"])]

    def __str__(self):
        dealer = self.bullion_dealer_org.display_name
        workshop = self.workshop_org.display_name
        return f"{dealer} -> {workshop}"

    def clean(self):
        """طبق ZRV-ERD-002 بخش ۱۰.۱: نوع سازمانی هر طرف باید درست باشد."""
        if self.bullion_dealer_org.organization_type != OrganizationType.BULLION_DEALER:
            raise ValidationError("bullion_dealer_org باید از نوع BULLION_DEALER باشد.")
        if self.workshop_org.organization_type != OrganizationType.WORKSHOP:
            raise ValidationError("workshop_org باید از نوع WORKSHOP باشد.")

        if self.recorded_by_membership is not None:
            valid_org_ids = {self.bullion_dealer_org_id, self.workshop_org_id}
            if self.recorded_by_membership.organization_id not in valid_org_ids:
                raise ValidationError(
                    "Membership ثبت‌کننده باید عضو یکی از دو طرف این درخواست باشد."
                )
