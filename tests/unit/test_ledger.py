from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.catalog.models import AssetType
from apps.identity.models import AccountRole, User
from apps.ledger.models import (
    GoldAccount,
    GoldAccountRetailerPosition,
    GoldLedgerLine,
    GoldLedgerLineDirection,
    GoldLedgerTransaction,
    GoldLedgerTransactionType,
)
from apps.tenancy.models import Organization, OrganizationType


@pytest.fixture
def buyer_user():
    return User.objects.create_user(
        mobile_e164="+989123330001", account_role=AccountRole.CONSUMER
    )


@pytest.fixture
def gold_account(buyer_user):
    return GoldAccount.objects.create(user=buyer_user)


@pytest.fixture
def retailer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی لجر",
        display_name="طلافروشی لجر",
    )


@pytest.fixture
def asset_type():
    return AssetType.objects.create(
        code="MELTED_GOLD_18K", display_name_fa="آبشده ۱۸ عیار", is_active=True
    )


@pytest.fixture
def position(gold_account, retailer_org, asset_type):
    return GoldAccountRetailerPosition.objects.create(
        gold_account=gold_account, organization=retailer_org, asset_type=asset_type
    )


def _make_transaction_with_line(position, direction, grams, idempotency_key):
    txn = GoldLedgerTransaction.objects.create(
        transaction_type=GoldLedgerTransactionType.BUYER_PURCHASE,
        occurred_at=timezone.now(),
        idempotency_key=idempotency_key,
    )
    GoldLedgerLine.objects.create(
        ledger_transaction=txn,
        gold_account_retailer_position=position,
        direction=direction,
        grams=Decimal(grams),
        price_per_gram_snapshot=Decimal("1000000"),
        amount_toman=Decimal(grams) * Decimal("1000000"),
    )
    return txn


@pytest.mark.django_db
def test_gold_account_is_one_per_user(buyer_user):
    GoldAccount.objects.create(user=buyer_user)
    with pytest.raises(IntegrityError):
        GoldAccount.objects.create(user=buyer_user)


@pytest.mark.django_db
def test_position_unique_per_account_org_asset_type(
    gold_account, retailer_org, asset_type
):
    GoldAccountRetailerPosition.objects.create(
        gold_account=gold_account, organization=retailer_org, asset_type=asset_type
    )
    with pytest.raises(IntegrityError):
        GoldAccountRetailerPosition.objects.create(
            gold_account=gold_account, organization=retailer_org, asset_type=asset_type
        )


@pytest.mark.django_db
def test_position_rejects_non_retailer_organization(gold_account, asset_type):
    dealer_org = Organization.objects.create(
        organization_type=OrganizationType.BULLION_DEALER,
        legal_name="بنکداری لجر",
        display_name="بنکداری لجر",
    )
    position = GoldAccountRetailerPosition(
        gold_account=gold_account, organization=dealer_org, asset_type=asset_type
    )
    with pytest.raises(ValidationError):
        position.clean()


@pytest.mark.django_db
def test_reconstruct_balance_is_zero_with_no_lines(position):
    assert position.reconstruct_balance_grams() == Decimal("0")


@pytest.mark.django_db
def test_reconstruct_balance_matches_credit_and_debit_lines(position):
    """
    Invariant حیاتی ZRV-ERD-002 بخش ۷.۴:
    Balance باید همیشه برابر Σ CREDIT − Σ DEBIT باشد.

    سناریو: خرید ۱۰ گرم (CREDIT)، سپس فروش ۳ گرم (DEBIT) →
    Balance واقعی باید ۷ گرم باشد.
    """
    _make_transaction_with_line(
        position, GoldLedgerLineDirection.CREDIT, "10", "idem-purchase-1"
    )
    _make_transaction_with_line(
        position, GoldLedgerLineDirection.DEBIT, "3", "idem-sale-1"
    )

    assert position.reconstruct_balance_grams() == Decimal("7")


@pytest.mark.django_db
def test_reconstruct_balance_after_multiple_purchases(position):
    """سناریوی Micro-Purchase: چند خرید کوچک باید جمع درست بدهند."""
    _make_transaction_with_line(
        position, GoldLedgerLineDirection.CREDIT, "0.005", "idem-micro-1"
    )
    _make_transaction_with_line(
        position, GoldLedgerLineDirection.CREDIT, "0.012", "idem-micro-2"
    )
    _make_transaction_with_line(
        position, GoldLedgerLineDirection.CREDIT, "0.020", "idem-micro-3"
    )

    assert position.reconstruct_balance_grams() == Decimal("0.037")


@pytest.mark.django_db
def test_idempotency_key_must_be_unique():
    GoldLedgerTransaction.objects.create(
        transaction_type=GoldLedgerTransactionType.BUYER_PURCHASE,
        occurred_at=timezone.now(),
        idempotency_key="same-key",
    )
    with pytest.raises(IntegrityError):
        GoldLedgerTransaction.objects.create(
            transaction_type=GoldLedgerTransactionType.BUYER_SALE,
            occurred_at=timezone.now(),
            idempotency_key="same-key",
        )


@pytest.mark.django_db
def test_ledger_line_grams_must_be_positive(position):
    """طبق ZRV-ERD-002: جهت با CREDIT/DEBIT مشخص می‌شود، نه با علامت منفی."""
    txn = GoldLedgerTransaction.objects.create(
        transaction_type=GoldLedgerTransactionType.ADJUSTMENT,
        occurred_at=timezone.now(),
        idempotency_key="idem-invalid",
    )
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            GoldLedgerLine.objects.create(
                ledger_transaction=txn,
                gold_account_retailer_position=position,
                direction=GoldLedgerLineDirection.CREDIT,
                grams=Decimal("-5"),
                price_per_gram_snapshot=Decimal("1000000"),
                amount_toman=Decimal("-5000000"),
            )


@pytest.mark.django_db
def test_two_different_retailers_keep_independent_positions(gold_account, asset_type):
    """
    پایه فنی قانون قفل فروش: موجودی نزد دو طلافروشی مختلف کاملاً مستقل
    است و هرگز با هم جمع/مخلوط نمی‌شود.
    """
    retailer_a = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی A",
        display_name="طلافروشی A",
    )
    retailer_b = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی B",
        display_name="طلافروشی B",
    )
    position_a = GoldAccountRetailerPosition.objects.create(
        gold_account=gold_account, organization=retailer_a, asset_type=asset_type
    )
    position_b = GoldAccountRetailerPosition.objects.create(
        gold_account=gold_account, organization=retailer_b, asset_type=asset_type
    )

    _make_transaction_with_line(
        position_a, GoldLedgerLineDirection.CREDIT, "5", "idem-a-1"
    )

    assert position_a.reconstruct_balance_grams() == Decimal("5")
    assert position_b.reconstruct_balance_grams() == Decimal("0")
