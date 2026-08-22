"""
RFID App — مرز داده‌ای زیرسیستم RFID

مرجع: ZRV-ERD-002 بخش ۶.۲ / ADR-016

⚠️ هشدار معماری: این App عمداً لاغر است و باید لاغر بماند. فقط دو
جدول Reference دارد و هیچ منطق Zone/Reader/Alert/Business Rule اینجا
نوشته نمی‌شود. اگر حین توسعه حس کردید این App دارد بزرگ می‌شود، یعنی
منطق در جای اشتباه نوشته شده - آن منطق باید در سرویس RFID مستقل
(طبق ADR-016) برود، نه اینجا.
"""

import uuid

from django.db import models


class RfidTagStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    INACTIVE = "INACTIVE", "غیرفعال"


class RfidTag(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۶.۲ / جدول `rfid_tags` — Reference سبک"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    epc = models.CharField(max_length=64, unique=True)
    organization = models.ForeignKey(
        "tenancy.Organization", on_delete=models.PROTECT, related_name="rfid_tags"
    )
    inventory_position = models.ForeignKey(
        "inventory.InventoryPosition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="rfid_tags",
    )
    status = models.CharField(
        max_length=16, choices=RfidTagStatus.choices, default=RfidTagStatus.ACTIVE
    )

    class Meta:
        app_label = "rfid"
        db_table = "rfid_tags"

    def __str__(self):
        return self.epc


class RfidSyncEventType(models.TextChoices):
    ITEM_DETECTED = "ITEM_DETECTED", "شناسایی شد"
    ITEM_MISSING = "ITEM_MISSING", "گم شد"
    ALERT_RAISED = "ALERT_RAISED", "هشدار صادر شد"


class RfidSyncEvent(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۶.۲ / جدول `rfid_sync_events` — Reference سبک"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="rfid_sync_events",
    )
    event_type = models.CharField(max_length=16, choices=RfidSyncEventType.choices)
    occurred_at = models.DateTimeField()
    raw_payload_ref = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "rfid"
        db_table = "rfid_sync_events"
        indexes = [models.Index(fields=["organization", "-occurred_at"])]
        ordering = ["-occurred_at"]

    def __str__(self):
        return f"{self.organization.display_name} - {self.event_type}"
