import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone

from apps.identity.models import AccountRole, User
from apps.tenancy.models import (
    Membership,
    MembershipRole,
    Organization,
    OrganizationContract,
    OrganizationType,
)


@pytest.mark.django_db
def test_organization_defaults_to_pending_contract():
    """
    طبق ZRV-FLOW-001: Onboarding خودسرویس نیست؛
    status از PENDING_CONTRACT شروع می‌شود.
    """
    org = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی نمونه",
        display_name="طلافروشی نمونه",
    )
    assert org.status == "PENDING_CONTRACT"


@pytest.mark.django_db
def test_organization_contract_is_one_to_one():
    """یک Organization در MVP0 فقط یک قرارداد فعال دارد."""
    org = Organization.objects.create(
        organization_type=OrganizationType.BULLION_DEALER,
        legal_name="بنکداری نمونه",
        display_name="بنکداری نمونه",
    )
    OrganizationContract.objects.create(
        organization=org, contract_reference="C-001", signed_at=timezone.now()
    )
    with pytest.raises(IntegrityError):
        OrganizationContract.objects.create(
            organization=org, contract_reference="C-002", signed_at=timezone.now()
        )


@pytest.mark.django_db
def test_membership_unique_per_org_and_user():
    org = Organization.objects.create(
        organization_type=OrganizationType.WORKSHOP,
        legal_name="طلاسازی نمونه",
        display_name="طلاسازی نمونه",
    )
    user = User.objects.create_user(
        mobile_e164="+989121110001", account_role=AccountRole.WORKSHOP_STAFF
    )
    Membership.objects.create(
        organization=org, user=user, membership_role=MembershipRole.OWNER
    )
    with pytest.raises(IntegrityError):
        Membership.objects.create(
            organization=org, user=user, membership_role=MembershipRole.STAFF
        )


@pytest.mark.django_db
def test_membership_role_mismatch_is_rejected_by_clean():
    """کارمند بنکداری نباید بتواند عضو یک طلافروشی شود."""
    retailer = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی X",
        display_name="طلافروشی X",
    )
    dealer_staff = User.objects.create_user(
        mobile_e164="+989121110002", account_role=AccountRole.BULLION_DEALER_STAFF
    )
    membership = Membership(
        organization=retailer,
        user=dealer_staff,
        membership_role=MembershipRole.STAFF,
    )
    with pytest.raises(ValidationError):
        membership.clean()


@pytest.mark.django_db
def test_membership_role_match_passes_clean():
    retailer = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="طلافروشی Y",
        display_name="طلافروشی Y",
    )
    retailer_staff = User.objects.create_user(
        mobile_e164="+989121110003", account_role=AccountRole.RETAILER_STAFF
    )
    membership = Membership(
        organization=retailer,
        user=retailer_staff,
        membership_role=MembershipRole.OWNER,
    )
    membership.clean()  # نباید Exception بدهد


@pytest.mark.django_db
def test_membership_query_is_scoped_per_organization():
    """
    مهم‌ترین تست این لایه (طبق ZRV-BOOT-001 بخش ۱): مقدمه‌ی Tenant
    Isolation. Membershipهای یک Organization هرگز نباید شامل Membership
    سازمان دیگر باشند.
    """
    org_a = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="سازمان A",
        display_name="سازمان A",
    )
    org_b = Organization.objects.create(
        organization_type=OrganizationType.RETAILER,
        legal_name="سازمان B",
        display_name="سازمان B",
    )
    user_a = User.objects.create_user(
        mobile_e164="+989121110004", account_role=AccountRole.RETAILER_STAFF
    )
    user_b = User.objects.create_user(
        mobile_e164="+989121110005", account_role=AccountRole.RETAILER_STAFF
    )
    Membership.objects.create(
        organization=org_a, user=user_a, membership_role=MembershipRole.OWNER
    )
    Membership.objects.create(
        organization=org_b, user=user_b, membership_role=MembershipRole.OWNER
    )

    org_a_members = Membership.objects.filter(organization=org_a)

    assert org_a_members.count() == 1
    assert org_a_members.first().user_id == user_a.id
    assert user_b.id not in org_a_members.values_list("user_id", flat=True)
