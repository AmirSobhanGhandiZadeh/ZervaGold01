"""
Inventory App

مرجع: ZRV-ERD-002 بخش ۶.۱ (دامنه موجودی)

موجودی فقط برای طلافروشی و بنکدار معنادار است (نه طلاساز - طبق
ZRV-FLOW-001 طلاساز فقط فروشنده است و موجودی رسمی روی پلتفرم ندارد).

این مدل مصرف‌کننده‌ی خروجی زیرسیستم RFID است (last_synced_from_rfid_at)
اما خودش هیچ منطق RFID ندارد - طبق ADR-016.
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.tenancy.models import OrganizationType

INVENTORY_ELIGIBLE_ORG_TYPES = {
    OrganizationType.RETAILER,
    OrganizationType.BULLION_DEALER,
}


class InventoryPosition(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۶.۱ / جدول `inventory_positions`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="inventory_positions",
    )
    asset_type = models.ForeignKey(
        "catalog.AssetType",
        on_delete=models.PROTECT,
        related_name="inventory_positions",
    )
    available_grams = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    reserved_grams = models.DecimalField(max_digits=18, decimal_places=6, default=0)
    last_synced_from_rfid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "inventory"
        db_table = "inventory_positions"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "asset_type"],
                name="uniq_inventory_position_org_asset",
            ),
            models.CheckConstraint(
                condition=models.Q(available_grams__gte=0),
                name="inventory_available_grams_non_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(reserved_grams__gte=0),
                name="inventory_reserved_grams_non_negative",
            ),
        ]

    def __str__(self):
        return f"{self.organization.display_name} / {self.asset_type.code}"

    def clean(self):
        """
        مرجع: ZRV-ERD-002 بخش ۶.۱ - Inventory Position فقط برای طلافروشی
        و بنکدار معنادار است، نه طلاساز.

        طبق اصل «Business Logic در save() ممنوع»، این Validation باید
        توسط Application Service آینده با full_clean() فراخوانی شود.
        """
        if self.organization.organization_type not in INVENTORY_ELIGIBLE_ORG_TYPES:
            raise ValidationError(
                "Inventory Position فقط برای طلافروشی یا بنکدار مجاز است."
            )
