"""
Platform App — زیرساخت مشترک (Audit / Outbox / Idempotency)

مرجع: ZRV-ERD-002 بخش ۱۱

این سه جدول Cross-Cutting و مشترک بین همه Appها هستند؛ به همین دلیل
Referenceهایشان به سایر Entityها Polymorphic است (entity_type + entity_id
برای Audit، aggregate_type + aggregate_id برای Outbox)، نه FK واقعی -
چون یک جدول واحد نمی‌تواند هم‌زمان به همه Entityهای پلتفرم FK بزند.
"""

import uuid

from django.db import models
from django.utils import timezone


class AuditEvent(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۱۱.۱ / جدول `audit_events`

    Append-Only است؛ هیچ Update/Delete روی رکورد ثبت‌شده مجاز نیست.
    حداقل رویدادهایی که باید Audit شوند: ورود موفق/ناموفق، ارتقا سطح
    KYC، تغییر اجرت طلافروشی، رد سفارش خریدار، هر رکورد b2b_ledger،
    تغییر status سازمان، افزودن/حذف عضویت.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    actor_user = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    actor_membership = models.ForeignKey(
        "tenancy.Membership",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=100)
    entity_type = models.CharField(max_length=100)
    entity_id = models.UUIDField()
    before_snapshot = models.JSONField(null=True, blank=True)
    after_snapshot = models.JSONField(null=True, blank=True)
    request_id = models.CharField(max_length=100, blank=True)
    correlation_id = models.CharField(max_length=100, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "platform"
        db_table = "audit_events"
        indexes = [
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["-occurred_at"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity_type}({self.entity_id})"

    @classmethod
    def record(
        cls,
        *,
        action,
        entity_type,
        entity_id,
        actor_user=None,
        actor_membership=None,
        before_snapshot=None,
        after_snapshot=None,
        request_id="",
        correlation_id="",
    ):
        """
        Helper نازک برای ثبت یک رویداد Audit - صرفاً یک Wrapper ساده
        روی create() است. تصمیم اینکه *چه زمانی* باید Audit ثبت شود،
        برعهده Application Service آینده است، نه این متد.
        """
        return cls.objects.create(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user=actor_user,
            actor_membership=actor_membership,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            request_id=request_id,
            correlation_id=correlation_id,
        )


class OutboxEventStatus(models.TextChoices):
    PENDING = "PENDING", "در انتظار"
    PROCESSING = "PROCESSING", "در حال پردازش"
    PUBLISHED = "PUBLISHED", "منتشرشده"
    FAILED = "FAILED", "ناموفق"


class OutboxEvent(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۱۱.۲ / جدول `outbox_events`

    هدف: جلوگیری از حالت «DB Commit موفق ولی Message Publish ناموفق»
    (طبق ADR-019). رکورد باید در همان Transaction تغییر State اصلی
    نوشته شود؛ Publish واقعی توسط یک Worker جدا (که هنوز ساخته نشده)
    انجام می‌شود.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=100)
    aggregate_type = models.CharField(max_length=100)
    aggregate_id = models.UUIDField()
    payload = models.JSONField()
    status = models.CharField(
        max_length=16,
        choices=OutboxEventStatus.choices,
        default=OutboxEventStatus.PENDING,
    )
    occurred_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        app_label = "platform"
        db_table = "outbox_events"
        indexes = [
            models.Index(fields=["status", "occurred_at"]),
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]

    def __str__(self):
        return f"{self.event_type} [{self.status}]"

    def mark_published(self):
        """Transition ساده وضعیت - بدون هیچ Side Effect بیرونی."""
        self.status = OutboxEventStatus.PUBLISHED
        self.published_at = timezone.now()
        self.save(update_fields=["status", "published_at"])

    def mark_failed(self):
        self.status = OutboxEventStatus.FAILED
        self.attempt_count = self.attempt_count + 1
        self.save(update_fields=["status", "attempt_count"])


class IdempotencyKeyStatus(models.TextChoices):
    PENDING = "PENDING", "در انتظار"
    COMPLETED = "COMPLETED", "تکمیل‌شده"


class IdempotencyKey(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۱۱.۳ / جدول `idempotency_keys`

    قانون (طبق ADR-020): همان Tenant + همان Command + همان Key = همان
    عملیات منطقی. Request تکراری با همان Key نباید Silent یک Transaction
    تجاری دوم بسازد.
    """

    key = models.CharField(max_length=100, primary_key=True)
    scope = models.CharField(max_length=100)
    request_hash = models.CharField(max_length=64)
    response_reference = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=16,
        choices=IdempotencyKeyStatus.choices,
        default=IdempotencyKeyStatus.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        app_label = "platform"
        db_table = "idempotency_keys"
        indexes = [models.Index(fields=["scope", "expires_at"])]

    def __str__(self):
        return f"{self.scope}:{self.key}"
