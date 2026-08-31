"""
Ledger App — حساب طلای خریدار

مرجع: ZRV-ERD-002 بخش ۷ (دامنه حساب طلای خریدار)

Invariant حیاتی (ZRV-ERD-002 بخش ۷.۴):
    balance هر Position باید همیشه برابر Σ CREDIT − Σ DEBIT از
    GoldLedgerLine باشد. اگر مغایرت داشت، یعنی یک باگ داده‌ای رخ داده،
    نه یک حالت عادی.

نکته وابستگی بین‌اپی (طبق ZRV-ENG-002 بخش ۷): GoldLedgerTransaction در
مدل بلندمدت به consumer.BuyerOrder ارجاع می‌دهد (source_order_id)، اما
چون consumer در Commit 8 ساخته می‌شود، این فیلد عمداً از این Commit
غایب است و در Commit 8 با یک Migration جدا (AddField) اضافه خواهد شد.
"""

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Case, DecimalField, Sum, When

from apps.tenancy.models import OrganizationType


class GoldAccountStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    FROZEN = "FROZEN", "مسدود"


class GoldAccount(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۷.۱ / جدول `gold_accounts`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        "identity.User", on_delete=models.PROTECT, related_name="gold_account"
    )
    status = models.CharField(
        max_length=16,
        choices=GoldAccountStatus.choices,
        default=GoldAccountStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "ledger"
        db_table = "gold_accounts"

    def __str__(self):
        return f"GoldAccount({self.user.mobile_e164})"


class GoldAccountRetailerPosition(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۷.۲ / جدول `gold_account_retailer_positions`

    این جدول خودِ مکانیزمی است که قانون «خریدار فقط می‌تواند به همان
    طلافروشی که ازش خریده بفروشد» را Enforce می‌کند: چون موجودی به
    تفکیک هر Retailer در یک ردیف مجزا نگه‌داری می‌شود، از نظر فنی اصلاً
    امکان فروش یک Position متعلق به Retailer A به Retailer B وجود ندارد.

    balance_grams صرفاً یک Cache غیر Authoritative است؛ همیشه باید با
    reconstruct_balance_grams() قابل بازسازی و تایید باشد.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gold_account = models.ForeignKey(
        "ledger.GoldAccount",
        on_delete=models.PROTECT,
        related_name="retailer_positions",
    )
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="buyer_gold_positions",
    )
    asset_type = models.ForeignKey(
        "catalog.AssetType",
        on_delete=models.PROTECT,
        related_name="buyer_gold_positions",
    )
    balance_grams = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    available_grams = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    reserved_grams = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "ledger"
        db_table = "gold_account_retailer_positions"
        constraints = [
            models.UniqueConstraint(
                fields=["gold_account", "organization", "asset_type"],
                name="uniq_position_per_account_org_asset",
            ),
        ]

    def __str__(self):
        return f"{self.gold_account} @ {self.organization.display_name}"

    def clean(self):
        """طبق ZRV-FLOW-001: قانون قفل فروش فقط برای طلافروشی معنا دارد."""
        if self.organization.organization_type != OrganizationType.RETAILER:
            raise ValidationError(
                "Gold Account Retailer Position فقط برای سازمان از نوع "
                "RETAILER مجاز است."
            )

    def reconstruct_balance_grams(self) -> Decimal:
        """
        Balance را مستقیماً از GoldLedgerLine بازسازی می‌کند - نه از فیلد
        Cache شده balance_grams. این تابع مرجع تایید Invariant اصلی
        (ZRV-ERD-002 بخش ۷.۴) است.
        """
        aggregation = self.ledger_lines.aggregate(
            total=Sum(
                Case(
                    When(
                        direction=GoldLedgerLineDirection.CREDIT,
                        then=models.F("grams"),
                    ),
                    When(
                        direction=GoldLedgerLineDirection.DEBIT,
                        then=-models.F("grams"),
                    ),
                    output_field=DecimalField(max_digits=18, decimal_places=6),
                )
            )
        )
        return aggregation["total"] or Decimal("0")


class GoldLedgerTransactionType(models.TextChoices):
    BUYER_PURCHASE = "BUYER_PURCHASE", "خرید خریدار"
    BUYER_SALE = "BUYER_SALE", "فروش خریدار"
    ADJUSTMENT = "ADJUSTMENT", "اصلاحیه"


class GoldLedgerTransaction(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۷.۳ / جدول `gold_ledger_transactions`

<<<<<<< Updated upstream
    source_order اینجا (در Commit 8) اضافه شد؛ در Commit 7 عمداً غایب
    بود چون consumer.BuyerOrder هنوز وجود نداشت - طبق وابستگی دوطرفه‌ی
    مستند در ZRV-ENG-002 بخش ۷.
=======
    توجه: source_order_id (FK به consumer.BuyerOrder) عمداً از این
    Commit غایب است - در Commit 8 اضافه می‌شود.
>>>>>>> Stashed changes
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_type = models.CharField(
        max_length=20, choices=GoldLedgerTransactionType.choices
    )
<<<<<<< Updated upstream
    source_order = models.ForeignKey(
        "consumer.BuyerOrder",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ledger_transactions",
    )
=======
>>>>>>> Stashed changes
    occurred_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    idempotency_key = models.CharField(max_length=100, unique=True)

    class Meta:
        app_label = "ledger"
        db_table = "gold_ledger_transactions"
        indexes = [models.Index(fields=["transaction_type", "-occurred_at"])]

    def __str__(self):
        return f"{self.transaction_type} @ {self.occurred_at}"


class GoldLedgerLineDirection(models.TextChoices):
    CREDIT = "CREDIT", "بستانکار"
    DEBIT = "DEBIT", "بدهکار"


class GoldLedgerLine(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۷.۴ / جدول `gold_ledger_lines`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ledger_transaction = models.ForeignKey(
        "ledger.GoldLedgerTransaction",
        on_delete=models.PROTECT,
        related_name="lines",
    )
    gold_account_retailer_position = models.ForeignKey(
        "ledger.GoldAccountRetailerPosition",
        on_delete=models.PROTECT,
        related_name="ledger_lines",
    )
    direction = models.CharField(max_length=10, choices=GoldLedgerLineDirection.choices)
    grams = models.DecimalField(max_digits=18, decimal_places=6)
    price_per_gram_snapshot = models.DecimalField(max_digits=18, decimal_places=2)
    amount_toman = models.DecimalField(max_digits=18, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "ledger"
        db_table = "gold_ledger_lines"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(grams__gt=0),
                name="ledger_line_grams_positive",
            ),
        ]

    def __str__(self):
        return f"{self.direction} {self.grams}g"
