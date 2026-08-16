import pytest
from django.db import IntegrityError

from apps.identity.models import AccountRole, User


@pytest.mark.django_db
def test_create_user_has_unusable_password():
    """طبق ZRV-FLOW-001: احراز هویت فقط OTP است، کاربران عادی پسورد ندارند."""
    user = User.objects.create_user(
        mobile_e164="+989120000001", account_role=AccountRole.CONSUMER
    )
    assert user.has_usable_password() is False
    assert user.account_role == AccountRole.CONSUMER
    assert user.kyc_level == 0
    assert user.status == "ACTIVE"


@pytest.mark.django_db
def test_mobile_number_is_unique():
    """هر شماره موبایل = یک اکانت (نمی‌تواند تکراری باشد)."""
    User.objects.create_user(
        mobile_e164="+989120000002", account_role=AccountRole.CONSUMER
    )
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            mobile_e164="+989120000002", account_role=AccountRole.RETAILER_STAFF
        )


@pytest.mark.django_db
def test_verified_national_id_must_be_unique():
    """یک کد ملی Verify‌شده نباید روی دو اکانت هم‌زمان معتبر باشد."""
    User.objects.create_user(
        mobile_e164="+989120000003",
        account_role=AccountRole.CONSUMER,
        national_id="1234567890",
        national_id_verified=True,
    )
    with pytest.raises(IntegrityError):
        User.objects.create_user(
            mobile_e164="+989120000004",
            account_role=AccountRole.CONSUMER,
            national_id="1234567890",
            national_id_verified=True,
        )


@pytest.mark.django_db
def test_unverified_duplicate_national_id_is_allowed():
    """
    پیش از Verify شدن، تکراری بودن کد ملی مانع ثبت‌نام نمی‌شود
    (Constraint فقط روی verified=True است).
    """
    User.objects.create_user(
        mobile_e164="+989120000005",
        account_role=AccountRole.CONSUMER,
        national_id="1111111111",
        national_id_verified=False,
    )
    user2 = User.objects.create_user(
        mobile_e164="+989120000006",
        account_role=AccountRole.CONSUMER,
        national_id="1111111111",
        national_id_verified=False,
    )
    assert user2.national_id == "1111111111"
