from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.catalog.models import AssetType
from apps.consumer.models import (
    AutoApprovalPolicy,
    BuyerOrder,
    InternalInvoice,
    KycCheckResult,
    OrderDirection,
    OrderInputMode,
    OrderReservation,
)
from apps.identity.models import AccountRole, User
from apps.inventory.models import InventoryPosition
from apps.ledger.models import GoldAccount, GoldAccountRetailerPosition
from apps.tenancy.models import Organization, OrganizationType


@pytest.fixture
def retailer_a():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی A",
        display_name="طلافروشی A",
    )


@pytest.fixture
def retailer_b():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی B",
        display_name="طلافروشی B",
    )


@pytest.fixture
def asset_type():
    return AssetType.objects.create(
        code="MELTED_GOLD_18K", display_name_fa="آبشده ۱۸ عیار", is_active=True
    )


@pytest.fixture
def buyer_gold_account():
    user = User.objects.create_user(
        mobile_e164="+989124440001", account_role=AccountRole.CONSUMER
    )
    return GoldAccount.objects.create(user=user)


def _make_buy_order(gold_account, organization, asset_type, **overrides):
    defaults = {
        "gold_account": gold_account,
        "organization": organization,
        "asset_type": asset_type,
        "direction": OrderDirection.BUY,
        "input_mode": OrderInputMode.GRAM_TO_TOMAN,
        "requested_grams": Decimal("5"),
        "price_per_gram_snapshot": Decimal("1000000"),
        "computed_grams": Decimal("5"),
        "computed_toman_amount": Decimal("5000000"),
        "kyc_tier_at_request": 0,
        "kyc_check_result": KycCheckResult.PASSED,
        "idempotency_key": "idem-buy-default",
    }
    defaults.update(overrides)
    return BuyerOrder.objects.create(**defaults)


@pytest.mark.django_db
def test_buy_order_rejects_non_retailer_organization(buyer_gold_account, asset_type):
    dealer = Organization.objects.create(
        organization_type=OrganizationType.BULLION_DEALER,
        legal_name="بنکداری سفارش",
        display_name="بنکداری سفارش",
    )
    order = BuyerOrder(
        gold_account=buyer_gold_account,
        organization=dealer,
        asset_type=asset_type,
        direction=OrderDirection.BUY,
        input_mode=OrderInputMode.GRAM_TO_TOMAN,
        requested_grams=Decimal("5"),
        price_per_gram_snapshot=Decimal("1000000"),
        computed_grams=Decimal("5"),
        computed_toman_amount=Decimal("5000000"),
        kyc_tier_at_request=0,
        kyc_check_result=KycCheckResult.PASSED,
        idempotency_key="idem-reject-1",
    )
    with pytest.raises(ValidationError):
        order.clean()


@pytest.mark.django_db
def test_buy_order_requires_an_amount(buyer_gold_account, retailer_a, asset_type):
    order = BuyerOrder(
        gold_account=buyer_gold_account,
        organization=retailer_a,
        asset_type=asset_type,
        direction=OrderDirection.BUY,
        input_mode=OrderInputMode.GRAM_TO_TOMAN,
        price_per_gram_snapshot=Decimal("1000000"),
        computed_grams=Decimal("0"),
        computed_toman_amount=Decimal("0"),
        kyc_tier_at_request=0,
        kyc_check_result=KycCheckResult.PASSED,
        idempotency_key="idem-reject-2",
    )
    with pytest.raises(ValidationError):
        order.clean()


@pytest.mark.django_db
def test_buy_reservation_requires_matching_retailer_inventory(
    buyer_gold_account, retailer_a, retailer_b, asset_type
):
    """رزرو خرید نباید بتواند موجودی یک طلافروشی دیگر را هدف بگیرد."""
    order = _make_buy_order(
        buyer_gold_account, retailer_a, asset_type, idempotency_key="idem-buy-1"
    )
    wrong_position = InventoryPosition.objects.create(
        organization=retailer_b, asset_type=asset_type, available_grams=Decimal("100")
    )
    reservation = OrderReservation(
        buyer_order=order,
        inventory_position=wrong_position,
        reserved_grams=Decimal("5"),
        expires_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        reservation.clean()


@pytest.mark.django_db
def test_buy_reservation_with_correct_retailer_passes(
    buyer_gold_account, retailer_a, asset_type
):
    order = _make_buy_order(
        buyer_gold_account, retailer_a, asset_type, idempotency_key="idem-buy-2"
    )
    position = InventoryPosition.objects.create(
        organization=retailer_a, asset_type=asset_type, available_grams=Decimal("100")
    )
    reservation = OrderReservation(
        buyer_order=order,
        inventory_position=position,
        reserved_grams=Decimal("5"),
        expires_at=timezone.now(),
    )
    reservation.clean()  # نباید Exception بدهد


@pytest.mark.django_db
def test_sell_reservation_rejects_mismatched_retailer(
    buyer_gold_account, retailer_a, retailer_b, asset_type
):
    """
    مهم‌ترین تست این Commit: قانون قفل فروش. خریداری که از طلافروشی A
    خریده، نباید بتواند سفارش فروش را به موجودی نزد طلافروشی B وصل کند.
    """
    sell_order = _make_buy_order(
        buyer_gold_account,
        retailer_a,
        asset_type,
        direction=OrderDirection.SELL,
        idempotency_key="idem-sell-1",
    )
    position_at_b = GoldAccountRetailerPosition.objects.create(
        gold_account=buyer_gold_account, organization=retailer_b, asset_type=asset_type
    )
    reservation = OrderReservation(
        buyer_order=sell_order,
        gold_account_retailer_position=position_at_b,
        reserved_grams=Decimal("5"),
        expires_at=timezone.now(),
    )
    with pytest.raises(ValidationError):
        reservation.clean()


@pytest.mark.django_db
def test_sell_reservation_with_correct_retailer_passes(
    buyer_gold_account, retailer_a, asset_type
):
    """فروش به همان طلافروشی خرید باید مجاز باشد."""
    sell_order = _make_buy_order(
        buyer_gold_account,
        retailer_a,
        asset_type,
        direction=OrderDirection.SELL,
        idempotency_key="idem-sell-2",
    )
    position_at_a = GoldAccountRetailerPosition.objects.create(
        gold_account=buyer_gold_account, organization=retailer_a, asset_type=asset_type
    )
    reservation = OrderReservation(
        buyer_order=sell_order,
        gold_account_retailer_position=position_at_a,
        reserved_grams=Decimal("5"),
        expires_at=timezone.now(),
    )
    reservation.clean()  # نباید Exception بدهد


@pytest.mark.django_db
def test_auto_approval_policy_can_be_global_or_org_scoped(retailer_a):
    global_policy = AutoApprovalPolicy.objects.create()
    org_policy = AutoApprovalPolicy.objects.create(organization=retailer_a)

    assert global_policy.organization is None
    assert global_policy.is_active is True
    assert org_policy.organization == retailer_a


@pytest.mark.django_db
def test_internal_invoice_number_is_unique(buyer_gold_account, retailer_a, asset_type):
    order1 = _make_buy_order(
        buyer_gold_account, retailer_a, asset_type, idempotency_key="idem-inv-1"
    )
    order2 = _make_buy_order(
        buyer_gold_account, retailer_a, asset_type, idempotency_key="idem-inv-2"
    )
    InternalInvoice.objects.create(
        buyer_order=order1,
        invoice_number="INV-1405-000001",
        organization=retailer_a,
        gold_account=buyer_gold_account,
        grams=Decimal("5"),
        amount_toman=Decimal("5000000"),
        issued_at=timezone.now(),
    )
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        InternalInvoice.objects.create(
            buyer_order=order2,
            invoice_number="INV-1405-000001",
            organization=retailer_a,
            gold_account=buyer_gold_account,
            grams=Decimal("3"),
            amount_toman=Decimal("3000000"),
            issued_at=timezone.now(),
        )
