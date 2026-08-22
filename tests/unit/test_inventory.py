from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.catalog.models import AssetType
from apps.inventory.models import InventoryPosition
from apps.tenancy.models import Organization, OrganizationType


@pytest.fixture
def retailer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی موجودی",
        display_name="طلافروشی موجودی",
    )


@pytest.fixture
def workshop_org():
    return Organization.objects.create(
        organization_type=OrganizationType.WORKSHOP,
        legal_name="طلاسازی موجودی",
        display_name="طلاسازی موجودی",
    )


@pytest.fixture
def asset_type():
    return AssetType.objects.create(
        code="MELTED_GOLD_18K", display_name_fa="آبشده ۱۸ عیار", is_active=True
    )


@pytest.mark.django_db
def test_inventory_position_unique_per_org_and_asset_type(retailer_org, asset_type):
    InventoryPosition.objects.create(
        organization=retailer_org,
        asset_type=asset_type,
        available_grams=Decimal("500"),
    )
    with pytest.raises(IntegrityError):
        InventoryPosition.objects.create(
            organization=retailer_org,
            asset_type=asset_type,
            available_grams=Decimal("100"),
        )


@pytest.mark.django_db
def test_available_grams_cannot_be_negative(retailer_org, asset_type):
    """طبق ZRV-ERD-002 بخش ۶.۱: available_grams >= 0 در سطح دیتابیس Enforce می‌شود."""
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InventoryPosition.objects.create(
                organization=retailer_org,
                asset_type=asset_type,
                available_grams=Decimal("-10"),
            )


@pytest.mark.django_db
def test_reserved_grams_cannot_be_negative(retailer_org, asset_type):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            InventoryPosition.objects.create(
                organization=retailer_org,
                asset_type=asset_type,
                available_grams=Decimal("100"),
                reserved_grams=Decimal("-1"),
            )


@pytest.mark.django_db
def test_workshop_organization_cannot_have_inventory_position(workshop_org, asset_type):
    """طلاساز موجودی رسمی روی پلتفرم ندارد (طبق ZRV-FLOW-001)."""
    position = InventoryPosition(
        organization=workshop_org,
        asset_type=asset_type,
        available_grams=Decimal("100"),
    )
    with pytest.raises(ValidationError):
        position.clean()


@pytest.mark.django_db
def test_bullion_dealer_can_have_inventory_position(asset_type):
    dealer_org = Organization.objects.create(
        organization_type=OrganizationType.BULLION_DEALER,
        legal_name="بنکداری موجودی",
        display_name="بنکداری موجودی",
    )
    position = InventoryPosition(
        organization=dealer_org,
        asset_type=asset_type,
        available_grams=Decimal("10000"),
    )
    position.clean()  # نباید Exception بدهد
