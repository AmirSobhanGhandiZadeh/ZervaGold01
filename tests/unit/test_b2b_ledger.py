from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.b2b_ledger.models import (
    DealerRetailerAccount,
    DealerRetailerEntryType,
    DealerRetailerLedgerEntry,
    WorkshopPurchaseRequest,
)
from apps.identity.models import AccountRole, User
from apps.tenancy.models import (
    Membership,
    MembershipRole,
    Organization,
    OrganizationType,
)


@pytest.fixture
def dealer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.BULLION_DEALER,
        legal_name="بنکداری B2B",
        display_name="بنکداری B2B",
    )


@pytest.fixture
def retailer_org():
    return Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی B2B",
        display_name="طلافروشی B2B",
    )


@pytest.fixture
def workshop_org():
    return Organization.objects.create(
        organization_type=OrganizationType.WORKSHOP,
        legal_name="طلاسازی B2B",
        display_name="طلاسازی B2B",
    )


@pytest.fixture
def dealer_membership(dealer_org):
    user = User.objects.create_user(
        mobile_e164="+989125550001", account_role=AccountRole.BULLION_DEALER_STAFF
    )
    return Membership.objects.create(
        organization=dealer_org, user=user, membership_role=MembershipRole.OWNER
    )


@pytest.fixture
def retailer_membership(retailer_org):
    user = User.objects.create_user(
        mobile_e164="+989125550002", account_role=AccountRole.RETAILER_STAFF
    )
    return Membership.objects.create(
        organization=retailer_org, user=user, membership_role=MembershipRole.OWNER
    )


@pytest.fixture
def account(dealer_org, retailer_org):
    return DealerRetailerAccount.objects.create(
        bullion_dealer_org=dealer_org, retailer_org=retailer_org
    )


@pytest.mark.django_db
def test_account_unique_per_dealer_retailer_pair(dealer_org, retailer_org):
    from django.db import IntegrityError

    DealerRetailerAccount.objects.create(
        bullion_dealer_org=dealer_org, retailer_org=retailer_org
    )
    with pytest.raises(IntegrityError):
        DealerRetailerAccount.objects.create(
            bullion_dealer_org=dealer_org, retailer_org=retailer_org
        )


@pytest.mark.django_db
def test_account_clean_rejects_swapped_organization_types(dealer_org, retailer_org):
    """یک طلافروشی نمی‌تواند در نقش bullion_dealer_org قرار بگیرد."""
    account = DealerRetailerAccount(
        bullion_dealer_org=retailer_org, retailer_org=dealer_org
    )
    with pytest.raises(ValidationError):
        account.clean()


@pytest.mark.django_db
def test_gold_withdrawal_requires_grams_and_price(account, dealer_membership):
    entry = DealerRetailerLedgerEntry(
        account=account,
        entry_type=DealerRetailerEntryType.GOLD_WITHDRAWAL,
        amount_toman=Decimal("2000000000"),
        occurred_at=timezone.now(),
        recorded_by_membership=dealer_membership,
    )
    with pytest.raises(ValidationError):
        entry.clean()


@pytest.mark.django_db
def test_settlement_payment_rejects_grams(account, dealer_membership):
    entry = DealerRetailerLedgerEntry(
        account=account,
        entry_type=DealerRetailerEntryType.SETTLEMENT_PAYMENT,
        grams=Decimal("1"),
        amount_toman=Decimal("500000000"),
        occurred_at=timezone.now(),
        recorded_by_membership=dealer_membership,
    )
    with pytest.raises(ValidationError):
        entry.clean()


@pytest.mark.django_db
def test_recorder_must_belong_to_one_side_of_account(account):
    """کارمند یک سازمان کاملاً بی‌ربط نباید بتواند رکورد ثبت کند."""
    outsider_org = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی بی‌ربط",
        display_name="طلافروشی بی‌ربط",
    )
    outsider_user = User.objects.create_user(
        mobile_e164="+989125550003", account_role=AccountRole.RETAILER_STAFF
    )
    outsider_membership = Membership.objects.create(
        organization=outsider_org,
        user=outsider_user,
        membership_role=MembershipRole.OWNER,
    )
    entry = DealerRetailerLedgerEntry(
        account=account,
        entry_type=DealerRetailerEntryType.SETTLEMENT_PAYMENT,
        amount_toman=Decimal("500000000"),
        occurred_at=timezone.now(),
        recorded_by_membership=outsider_membership,
    )
    with pytest.raises(ValidationError):
        entry.clean()


@pytest.mark.django_db
def test_reconstruct_balance_matches_documented_example(
    account, dealer_membership, retailer_membership
):
    """
    مصداق دقیقاً تایید‌شده در گفتگو و ZRV-ERD-002 بخش ۹.۲:

    ردیف ۱: برداشت ۱۰ کیلوگرم به ارزش ۲,۰۰۰,۰۰۰,۰۰۰ تومان → مانده ۲ میلیارد
    ردیف ۲: تسویه ۵۰۰,۰۰۰,۰۰۰ تومان → مانده ۱.۵ میلیارد
    ردیف ۳: برداشت ۱ کیلوگرم به ارزش ۴۰۰,۰۰۰,۰۰۰ تومان → مانده ۱.۹ میلیارد
    """
    DealerRetailerLedgerEntry.objects.create(
        account=account,
        entry_type=DealerRetailerEntryType.GOLD_WITHDRAWAL,
        grams=Decimal("10000"),
        price_per_gram_at_transaction=Decimal("200000"),
        amount_toman=Decimal("2000000000"),
        occurred_at=timezone.now(),
        recorded_by_membership=retailer_membership,
    )
    assert account.reconstruct_balance_toman() == Decimal("2000000000")

    DealerRetailerLedgerEntry.objects.create(
        account=account,
        entry_type=DealerRetailerEntryType.SETTLEMENT_PAYMENT,
        amount_toman=Decimal("500000000"),
        occurred_at=timezone.now(),
        recorded_by_membership=retailer_membership,
    )
    assert account.reconstruct_balance_toman() == Decimal("1500000000")

    DealerRetailerLedgerEntry.objects.create(
        account=account,
        entry_type=DealerRetailerEntryType.GOLD_WITHDRAWAL,
        grams=Decimal("1000"),
        price_per_gram_at_transaction=Decimal("400000"),
        amount_toman=Decimal("400000000"),
        occurred_at=timezone.now(),
        recorded_by_membership=retailer_membership,
    )
    assert account.reconstruct_balance_toman() == Decimal("1900000000")


@pytest.mark.django_db
def test_workshop_request_clean_rejects_wrong_org_types(retailer_org, workshop_org):
    """طلافروشی نمی‌تواند به‌جای بنکدار در این رابطه قرار بگیرد."""
    request = WorkshopPurchaseRequest(
        bullion_dealer_org=retailer_org, workshop_org=workshop_org
    )
    with pytest.raises(ValidationError):
        request.clean()


@pytest.mark.django_db
def test_workshop_request_defaults_are_pending(dealer_org, workshop_org):
    request = WorkshopPurchaseRequest.objects.create(
        bullion_dealer_org=dealer_org, workshop_org=workshop_org
    )
    assert request.delivery_status == "PENDING"
    assert request.payment_status == "PENDING"


@pytest.mark.django_db
def test_workshop_request_recorder_must_belong_to_one_side(
    dealer_org, workshop_org, dealer_membership
):
    request = WorkshopPurchaseRequest(
        bullion_dealer_org=dealer_org,
        workshop_org=workshop_org,
        recorded_by_membership=dealer_membership,
    )
    request.clean()  # نباید Exception بدهد - dealer_membership عضو dealer_org است
