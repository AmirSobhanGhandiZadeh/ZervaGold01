from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from apps.catalog.models import AssetType
from apps.identity.models import AccountRole, User
from apps.pricing.models import (
    LaborFeeType,
    MarketQuote,
    PricingProvider,
    RetailerProductPricing,
)
from apps.tenancy.models import (
    Membership,
    MembershipRole,
    Organization,
    OrganizationType,
)
from common.constants import gram_to_mesghal_price


@pytest.fixture
def retailer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی نمونه",
        display_name="طلافروشی نمونه",
    )


@pytest.fixture
def bullion_dealer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.BULLION_DEALER,
        legal_name="بنکداری نمونه",
        display_name="بنکداری نمونه",
    )


@pytest.fixture
def retailer_membership(retailer_org):
    user = User.objects.create_user(
        mobile_e164="+989122220001", account_role=AccountRole.RETAILER_STAFF
    )
    return Membership.objects.create(
        organization=retailer_org, user=user, membership_role=MembershipRole.OWNER
    )


@pytest.fixture
def asset_type():
    return AssetType.objects.create(
        code="MELTED_GOLD_18K", display_name_fa="آبشده ۱۸ عیار", is_active=True
    )


@pytest.mark.django_db
def test_gram_to_mesghal_conversion():
    """طبق ZRV-ERD-002 بخش ۱.۵: ۱ مثقال = ۴.۳۳۱۸ گرم."""
    result = gram_to_mesghal_price(Decimal("1000000"))
    assert result == Decimal("4331800.00")


@pytest.mark.django_db
def test_market_quote_creation(asset_type):
    provider = PricingProvider.objects.create(code="BRSAPI", name="BrsApi.ir")
    quote = MarketQuote.objects.create(
        provider=provider,
        asset_type=asset_type,
        price_per_gram=Decimal("1000000"),
        price_per_mesghal=gram_to_mesghal_price(Decimal("1000000")),
        observed_at=timezone.now(),
    )
    assert quote.quality_status == "VALID"
    assert quote.price_per_mesghal == Decimal("4331800.00")


@pytest.mark.django_db
def test_only_one_active_pricing_per_org_and_asset_type(
    retailer_org, retailer_membership, asset_type
):
    """
    قانون کلیدی ZRV-ENG-002 بخش ۶: فقط یک تنظیم اجرت فعال هم‌زمان برای
    هر (طلافروشی، نوع دارایی) مجاز است.
    """
    RetailerProductPricing.objects.create(
        organization=retailer_org,
        asset_type=asset_type,
        labor_fee_type=LaborFeeType.PERCENTAGE,
        labor_fee_value=Decimal("7"),
        effective_from=timezone.now(),
        created_by_membership=retailer_membership,
    )
    with pytest.raises(IntegrityError):
        RetailerProductPricing.objects.create(
            organization=retailer_org,
            asset_type=asset_type,
            labor_fee_type=LaborFeeType.FIXED_PER_GRAM,
            labor_fee_value=Decimal("50000"),
            effective_from=timezone.now(),
            created_by_membership=retailer_membership,
        )


@pytest.mark.django_db
def test_closing_old_pricing_allows_new_active_one(
    retailer_org, retailer_membership, asset_type
):
    """بستن effective_to رکورد قبلی باید اجازه‌ی ثبت تنظیم جدید را بدهد."""
    old = RetailerProductPricing.objects.create(
        organization=retailer_org,
        asset_type=asset_type,
        labor_fee_type=LaborFeeType.PERCENTAGE,
        labor_fee_value=Decimal("7"),
        effective_from=timezone.now(),
        created_by_membership=retailer_membership,
    )
    old.effective_to = timezone.now()
    old.save(update_fields=["effective_to"])

    new = RetailerProductPricing.objects.create(
        organization=retailer_org,
        asset_type=asset_type,
        labor_fee_type=LaborFeeType.PERCENTAGE,
        labor_fee_value=Decimal("8"),
        effective_from=timezone.now(),
        created_by_membership=retailer_membership,
    )
    assert new.pk is not None


@pytest.mark.django_db
def test_only_retailer_organization_can_set_pricing(bullion_dealer_org, asset_type):
    """بنکدار/طلاساز نباید بتوانند اجرت محصول تنظیم کنند."""
    dealer_user = User.objects.create_user(
        mobile_e164="+989122220002", account_role=AccountRole.BULLION_DEALER_STAFF
    )
    dealer_membership = Membership.objects.create(
        organization=bullion_dealer_org,
        user=dealer_user,
        membership_role=MembershipRole.OWNER,
    )
    pricing = RetailerProductPricing(
        organization=bullion_dealer_org,
        asset_type=asset_type,
        labor_fee_type=LaborFeeType.PERCENTAGE,
        labor_fee_value=Decimal("7"),
        effective_from=timezone.now(),
        created_by_membership=dealer_membership,
    )
    with pytest.raises(ValidationError):
        pricing.clean()


@pytest.mark.django_db
def test_membership_from_different_org_is_rejected(retailer_org, asset_type):
    """کارمند طلافروشی دیگر نباید بتواند برای این سازمان اجرت ثبت کند."""
    other_org = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی دیگر",
        display_name="طلافروشی دیگر",
    )
    other_user = User.objects.create_user(
        mobile_e164="+989122220003", account_role=AccountRole.RETAILER_STAFF
    )
    other_membership = Membership.objects.create(
        organization=other_org, user=other_user, membership_role=MembershipRole.OWNER
    )
    pricing = RetailerProductPricing(
        organization=retailer_org,
        asset_type=asset_type,
        labor_fee_type=LaborFeeType.PERCENTAGE,
        labor_fee_value=Decimal("7"),
        effective_from=timezone.now(),
        created_by_membership=other_membership,
    )
    with pytest.raises(ValidationError):
        pricing.clean()
