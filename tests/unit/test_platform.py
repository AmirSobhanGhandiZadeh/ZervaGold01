import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.identity.models import AccountRole, User
from apps.platform.models import (
    AuditEvent,
    IdempotencyKey,
    OutboxEvent,
    OutboxEventStatus,
)


@pytest.mark.django_db
def test_audit_event_record_helper_creates_entry():
    user = User.objects.create_user(
        mobile_e164="+989126660001", account_role=AccountRole.CONSUMER
    )
    entity_id = uuid.uuid4()

    event = AuditEvent.record(
        action="ORDER_REJECTED",
        entity_type="BuyerOrder",
        entity_id=entity_id,
        actor_user=user,
        before_snapshot={"status": "RESERVED"},
        after_snapshot={"status": "REJECTED"},
        request_id="req-123",
        correlation_id="corr-123",
    )

    assert event.id is not None
    assert event.entity_id == entity_id
    assert event.before_snapshot == {"status": "RESERVED"}
    assert event.after_snapshot == {"status": "REJECTED"}


@pytest.mark.django_db
def test_audit_event_can_have_no_actor():
    """رویدادهای سیستمی (مثل Job زمان‌بندی‌شده) ممکن است actor نداشته باشند."""
    event = AuditEvent.record(
        action="RESERVATION_EXPIRED",
        entity_type="OrderReservation",
        entity_id=uuid.uuid4(),
    )
    assert event.actor_user is None
    assert event.actor_membership is None


@pytest.mark.django_db
def test_outbox_event_defaults_to_pending():
    event = OutboxEvent.objects.create(
        event_type="DealAccepted",
        aggregate_type="BuyerOrder",
        aggregate_id=uuid.uuid4(),
        payload={"grams": "5.000000"},
    )
    assert event.status == OutboxEventStatus.PENDING
    assert event.attempt_count == 0
    assert event.published_at is None


@pytest.mark.django_db
def test_outbox_event_mark_published_sets_timestamp():
    event = OutboxEvent.objects.create(
        event_type="DealAccepted",
        aggregate_type="BuyerOrder",
        aggregate_id=uuid.uuid4(),
        payload={},
    )
    event.mark_published()
    event.refresh_from_db()
    assert event.status == OutboxEventStatus.PUBLISHED
    assert event.published_at is not None


@pytest.mark.django_db
def test_outbox_event_mark_failed_increments_attempt_count():
    event = OutboxEvent.objects.create(
        event_type="DealAccepted",
        aggregate_type="BuyerOrder",
        aggregate_id=uuid.uuid4(),
        payload={},
    )
    event.mark_failed()
    event.mark_failed()
    event.refresh_from_db()
    assert event.status == OutboxEventStatus.FAILED
    assert event.attempt_count == 2


@pytest.mark.django_db
def test_idempotency_key_is_unique():
    IdempotencyKey.objects.create(
        key="idem-abc",
        scope="buyer_orders.create",
        request_hash="hash1",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    with pytest.raises(IntegrityError):
        IdempotencyKey.objects.create(
            key="idem-abc",
            scope="buyer_orders.create",
            request_hash="hash2",
            expires_at=timezone.now() + timedelta(hours=1),
        )


@pytest.mark.django_db
def test_idempotency_key_default_status_is_pending():
    key = IdempotencyKey.objects.create(
        key="idem-xyz",
        scope="dealer_retailer_ledger_entries.create",
        request_hash="hash3",
        expires_at=timezone.now() + timedelta(hours=1),
    )
    assert key.status == "PENDING"
