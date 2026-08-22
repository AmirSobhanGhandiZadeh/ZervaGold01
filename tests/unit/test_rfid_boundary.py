from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.catalog.models import AssetType
from apps.inventory.models import InventoryPosition
from apps.rfid.models import RfidSyncEvent, RfidSyncEventType, RfidTag
from apps.tenancy.models import Organization, OrganizationType


@pytest.fixture
def retailer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی RFID",
        display_name="طلافروشی RFID",
    )


@pytest.mark.django_db
def test_epc_is_globally_unique(retailer_org):
    RfidTag.objects.create(epc="E200001122334455", organization=retailer_org)
    with pytest.raises(IntegrityError):
        RfidTag.objects.create(epc="E200001122334455", organization=retailer_org)


@pytest.mark.django_db
def test_rfid_tag_can_exist_without_inventory_position(retailer_org):
    """یک Tag ممکن است هنوز به هیچ Position مشخصی Assign نشده باشد."""
    tag = RfidTag.objects.create(epc="E200009988776655", organization=retailer_org)
    assert tag.inventory_position is None
    assert tag.status == "ACTIVE"


@pytest.mark.django_db
def test_rfid_tag_links_to_inventory_position(retailer_org):
    asset_type = AssetType.objects.create(
        code="MELTED_GOLD_18K", display_name_fa="آبشده ۱۸ عیار", is_active=True
    )
    position = InventoryPosition.objects.create(
        organization=retailer_org,
        asset_type=asset_type,
        available_grams=Decimal("500"),
    )
    tag = RfidTag.objects.create(
        epc="E200001111222233",
        organization=retailer_org,
        inventory_position=position,
    )
    assert tag.inventory_position_id == position.id


@pytest.mark.django_db
def test_sync_events_are_append_only_and_ordered(retailer_org):
    """Read Eventها Append-Only هستند و بر اساس زمان مرتب می‌شوند (طبق ADR-016)."""
    RfidSyncEvent.objects.create(
        organization=retailer_org,
        event_type=RfidSyncEventType.ITEM_DETECTED,
        occurred_at=timezone.now(),
    )
    RfidSyncEvent.objects.create(
        organization=retailer_org,
        event_type=RfidSyncEventType.ITEM_MISSING,
        occurred_at=timezone.now(),
    )
    events = list(RfidSyncEvent.objects.filter(organization=retailer_org))
    assert len(events) == 2
    assert events[0].occurred_at >= events[1].occurred_at
