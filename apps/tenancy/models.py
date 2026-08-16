"""
Tenancy App

مرجع: ZRV-ERD-002 بخش ۴ (دامنه سازمان و عضویت)

قانون کلیدی طبق ZRV-FLOW-001: هیچ Organization توسط خود کسب‌وکار
خودسرویس ساخته نمی‌شود؛ فقط بعد از جلسه و تایید تیم زروا (بنابراین
status از PENDING_CONTRACT شروع می‌شود، نه ACTIVE).

مرز Multi-Tenant در MVP0 دقیقاً همین organization_id است
(طبق ZRV-ERD-002 بخش ۱، قرارداد شماره ۶).
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.identity.models import AccountRole


class OrganizationType(models.TextChoices):
    RETAILER = "RETAILER", "طلافروشی خرد"
    BULLION_DEALER = "BULLION_DEALER", "بنکدار"
    WORKSHOP = "WORKSHOP", "طلاساز"


class OrganizationStatus(models.TextChoices):
    PENDING_CONTRACT = "PENDING_CONTRACT", "در انتظار قرارداد"
    ACTIVE = "ACTIVE", "فعال"
    SUSPENDED = "SUSPENDED", "معلق"


# نگاشت organization_type -> account_role موردانتظار برای Memberهای آن
# (مرجع Cross-App عمدی و کوچک برای Validation؛ ارجاع FK همچنان رشته‌ای است)
ORGANIZATION_TYPE_TO_STAFF_ROLE = {
    OrganizationType.RETAILER: AccountRole.RETAILER_STAFF,
    OrganizationType.BULLION_DEALER: AccountRole.BULLION_DEALER_STAFF,
    OrganizationType.WORKSHOP: AccountRole.WORKSHOP_STAFF,
}


class Organization(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۴.۱ / جدول `organizations`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization_type = models.CharField(
        max_length=32, choices=OrganizationType.choices
    )
    legal_name = models.CharField(max_length=255)
    display_name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=OrganizationStatus.choices,
        default=OrganizationStatus.PENDING_CONTRACT,
    )
    onboarded_by_zerva_staff = models.CharField(max_length=150, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "tenancy"
        db_table = "organizations"
        indexes = [models.Index(fields=["organization_type", "status"])]

    def __str__(self):
        return f"{self.display_name} ({self.get_organization_type_display()})"


class ContractStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    TERMINATED = "TERMINATED", "خاتمه‌یافته"


class OrganizationContract(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۴.۲ / جدول `organization_contracts`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.OneToOneField(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="contract",
    )
    contract_reference = models.CharField(max_length=100)
    signed_at = models.DateTimeField()
    status = models.CharField(
        max_length=16, choices=ContractStatus.choices, default=ContractStatus.ACTIVE
    )
    notes = models.TextField(blank=True)

    class Meta:
        app_label = "tenancy"
        db_table = "organization_contracts"

    def __str__(self):
        return f"Contract({self.organization.display_name}, {self.contract_reference})"


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "مالک"
    STAFF = "STAFF", "کارمند"


class MembershipStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    REVOKED = "REVOKED", "لغوشده"


class Membership(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۴.۳ / جدول `memberships`

    هر رکورد تراکنش در سایر Appها (به‌جای ارجاع مستقیم به Organization)
    باید به همین Membership لینک شود تا مشخص باشد کدام کارمند اقدام را
    انجام داده - طبق الزام صریح ZRV-FLOW-001.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "tenancy.Organization",
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    user = models.ForeignKey(
        "identity.User",
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    membership_role = models.CharField(max_length=16, choices=MembershipRole.choices)
    status = models.CharField(
        max_length=16,
        choices=MembershipStatus.choices,
        default=MembershipStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "tenancy"
        db_table = "memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"], name="uniq_membership_org_user"
            ),
        ]
        indexes = [models.Index(fields=["organization", "status"])]

    def __str__(self):
        return f"{self.user.mobile_e164} @ {self.organization.display_name}"

    def clean(self):
        """
        اعتبارسنجی طبق ZRV-ERD-002 بخش ۴.۳: account_role کاربر باید با
        organization_type سازمان همخوانی داشته باشد (مثلاً یک RETAILER_STAFF
        نباید عضو یک Organization از نوع WORKSHOP شود).

        توجه: طبق اصل «Business Logic در save() ممنوع»، این Validation باید
        توسط Application Service آینده با full_clean() فراخوانی شود؛
        به‌صورت خودکار روی save() اجرا نمی‌شود.
        """
        expected_role = ORGANIZATION_TYPE_TO_STAFF_ROLE.get(
            self.organization.organization_type
        )
        if expected_role and self.user.account_role != expected_role:
            raise ValidationError(
                f"کاربر با نقش {self.user.account_role} نمی‌تواند عضو سازمانی "
                f"از نوع {self.organization.organization_type} شود "
                f"(نقش موردانتظار: {expected_role})."
            )
