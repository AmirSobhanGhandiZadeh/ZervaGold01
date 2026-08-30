from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.consumer.domain.policies import evaluate_kyc_limit


@pytest.fixture(autouse=True)
def kyc_tiers():
    """طبق ZRV-FLOW-001: سه سطح ۲۰/۵۰/نامحدود گرم."""
    call_command("seed_kyc_tiers")


@pytest.mark.django_db
def test_tier_0_within_limit_passes():
    assert evaluate_kyc_limit(kyc_tier=0, requested_grams=Decimal("15")) == "PASSED"


@pytest.mark.django_db
def test_tier_0_exactly_at_limit_passes():
    assert evaluate_kyc_limit(kyc_tier=0, requested_grams=Decimal("20")) == "PASSED"


@pytest.mark.django_db
def test_tier_0_above_limit_fails():
    assert (
        evaluate_kyc_limit(kyc_tier=0, requested_grams=Decimal("20.001"))
        == "FAILED_LIMIT"
    )


@pytest.mark.django_db
def test_tier_1_within_limit_passes():
    assert evaluate_kyc_limit(kyc_tier=1, requested_grams=Decimal("45")) == "PASSED"


@pytest.mark.django_db
def test_tier_1_above_limit_fails():
    assert (
        evaluate_kyc_limit(kyc_tier=1, requested_grams=Decimal("51")) == "FAILED_LIMIT"
    )


@pytest.mark.django_db
def test_tier_2_has_no_upper_limit():
    """طبق ZRV-FLOW-001: سطح ۲ فعلاً سقف تعریف‌شده‌ای ندارد (🧮 TBD)."""
    assert evaluate_kyc_limit(kyc_tier=2, requested_grams=Decimal("100000")) == "PASSED"


@pytest.mark.django_db
def test_undefined_tier_raises_value_error():
    with pytest.raises(ValueError):
        evaluate_kyc_limit(kyc_tier=99, requested_grams=Decimal("1"))
