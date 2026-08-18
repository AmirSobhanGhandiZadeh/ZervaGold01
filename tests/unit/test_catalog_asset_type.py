import pytest
from django.core.management import call_command
from django.db import IntegrityError

from apps.catalog.models import AssetType


@pytest.mark.django_db
def test_asset_type_code_is_unique():
    AssetType.objects.create(code="MELTED_GOLD_18K", display_name_fa="آبشده ۱۸ عیار")
    with pytest.raises(IntegrityError):
        AssetType.objects.create(code="MELTED_GOLD_18K", display_name_fa="تکراری")


@pytest.mark.django_db
def test_seed_command_creates_exactly_five_types():
    call_command("seed_asset_types")
    assert AssetType.objects.count() == 5


@pytest.mark.django_db
def test_seed_command_activates_only_melted_gold_18k():
    """
    قانون قفل‌شده در ZRV-FLOW-001: فقط یک نوع دارایی (آبشده ۱۸ عیار)
    در MVP0 قابل انتخاب است؛ بقیه در UI دیده می‌شوند ولی غیرفعال‌اند.
    """
    call_command("seed_asset_types")

    active_types = AssetType.objects.filter(is_active=True)
    assert active_types.count() == 1
    assert active_types.first().code == "MELTED_GOLD_18K"

    inactive_codes = set(
        AssetType.objects.filter(is_active=False).values_list("code", flat=True)
    )
    assert inactive_codes == {"COIN", "BULLION_BAR", "ONLINE_GOLD", "USED_JEWELRY"}


@pytest.mark.django_db
def test_seed_command_is_idempotent():
    call_command("seed_asset_types")
    call_command("seed_asset_types")
    assert AssetType.objects.count() == 5


@pytest.mark.django_db
def test_melted_gold_18k_purity_is_750():
    call_command("seed_asset_types")
    melted = AssetType.objects.get(code="MELTED_GOLD_18K")
    assert melted.purity == 750
