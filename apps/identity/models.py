"""
Identity App

مرجع: ZRV-ERD-002 بخش ۳ (دامنه هویت و احراز هویت)

قوانین کلیدی این App طبق ZRV-FLOW-001:
  - احراز هویت فقط با OTP است؛ کاربران عادی پسورد ندارند.
  - هر شماره موبایل = یک اکانت = یک نقش (account_role بعد از ایجاد Immutable
    است - این قانون در Application Service enforce می‌شود، نه اینجا).
  - kyc_level فقط برای account_role = CONSUMER معنادار است.
"""

import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class AccountRole(models.TextChoices):
    CONSUMER = "CONSUMER", "خریدار"
    RETAILER_STAFF = "RETAILER_STAFF", "کارمند طلافروشی"
    BULLION_DEALER_STAFF = "BULLION_DEALER_STAFF", "کارمند بنکداری"
    WORKSHOP_STAFF = "WORKSHOP_STAFF", "کارمند طلاسازی"
    ZERVA_ADMIN = "ZERVA_ADMIN", "ادمین زروا"


class UserStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "فعال"
    SUSPENDED = "SUSPENDED", "معلق"
    DELETED = "DELETED", "حذف‌شده"


class UserManager(BaseUserManager):
    """
    OTP-only Manager: هیچ‌جا پسورد به‌عنوان مسیر اصلی احراز هویت استفاده
    نمی‌شود. `create_superuser` تنها استثنای عمدی است — صرفاً برای دسترسی
    داخلی تیم زروا به Django Admin (طبق ZRV-BOOT-001 بخش ۷۸).
    """

    use_in_migrations = True

    def create_user(
        self, mobile_e164, account_role=AccountRole.CONSUMER, **extra_fields
    ):
        if not mobile_e164:
            raise ValueError("mobile_e164 الزامی است")
        user = self.model(
            mobile_e164=mobile_e164, account_role=account_role, **extra_fields
        )
        user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, mobile_e164, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("account_role", AccountRole.ZERVA_ADMIN)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser باید is_staff=True داشته باشد")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser باید is_superuser=True داشته باشد")

        user = self.model(mobile_e164=mobile_e164, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """مرجع: ZRV-ERD-002 بخش ۳.۲ / جدول `users`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    mobile_e164 = models.CharField(max_length=15, unique=True)
    account_role = models.CharField(max_length=32, choices=AccountRole.choices)

    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    national_id = models.CharField(max_length=10, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)

    national_id_verified = models.BooleanField(default=False)
    national_id_verified_at = models.DateTimeField(null=True, blank=True)

    bank_verified = models.BooleanField(default=False)
    bank_verified_at = models.DateTimeField(null=True, blank=True)

    kyc_level = models.PositiveSmallIntegerField(default=0)

    status = models.CharField(
        max_length=16, choices=UserStatus.choices, default=UserStatus.ACTIVE
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "mobile_e164"
    REQUIRED_FIELDS = []

    class Meta:
        app_label = "identity"
        db_table = "users"
        constraints = [
            models.UniqueConstraint(
                fields=["national_id"],
                condition=models.Q(national_id_verified=True),
                name="uniq_verified_national_id",
            ),
        ]

    def __str__(self):
        return self.mobile_e164


class OtpPurpose(models.TextChoices):
    LOGIN = "LOGIN", "ورود"
    SIGNUP = "SIGNUP", "ثبت‌نام"


class OtpVerification(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۳.۳ — کد هرگز Plaintext ذخیره نمی‌شود."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile_e164 = models.CharField(max_length=15, db_index=True)
    code_hash = models.CharField(max_length=255)
    purpose = models.CharField(max_length=16, choices=OtpPurpose.choices)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    ip_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "identity"
        db_table = "otp_verifications"
        indexes = [models.Index(fields=["mobile_e164", "created_at"])]

    def __str__(self):
        return f"OTP({self.mobile_e164}, {self.purpose})"


class KycProvider(models.TextChoices):
    CIVIL_REGISTRY = "CIVIL_REGISTRY", "ثبت‌احوال"
    BANKING_NETWORK = "BANKING_NETWORK", "شبکه بانکی"


class KycResult(models.TextChoices):
    PENDING = "PENDING", "در انتظار"
    APPROVED = "APPROVED", "تایید شد"
    REJECTED = "REJECTED", "رد شد"
    ERROR = "ERROR", "خطا"


class KycVerificationEvent(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۳.۴

    رکورد Append-Only است؛ حتی تلاش‌های ناموفق ارتقا سطح KYC نگه‌داری
    می‌شوند (برای Audit/Fraud Review).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "identity.User", on_delete=models.PROTECT, related_name="kyc_events"
    )
    requested_level = models.PositiveSmallIntegerField()
    provider = models.CharField(max_length=32, choices=KycProvider.choices)
    provider_reference = models.CharField(max_length=255, blank=True)
    result = models.CharField(
        max_length=16, choices=KycResult.choices, default=KycResult.PENDING
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = "identity"
        db_table = "kyc_verification_events"
        indexes = [models.Index(fields=["user", "requested_at"])]

    def __str__(self):
        return (
            f"KYC({self.user.mobile_e164}, tier={self.requested_level}, {self.result})"
        )


class KycTierPolicy(models.Model):
    """
    مرجع: ZRV-ERD-002 بخش ۳.۵ — جدول Config/Reference، نه داده کاربر.
    Seed می‌شود؛ به‌ازای هر Tier حداکثر یک رکورد.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tier = models.PositiveSmallIntegerField(unique=True)
    max_grams_per_transaction = models.DecimalField(
        max_digits=18, decimal_places=6, null=True, blank=True
    )
    required_verification = models.CharField(max_length=255)
    description_fa = models.CharField(max_length=255)

    class Meta:
        app_label = "identity"
        db_table = "kyc_tier_policies"
        ordering = ["tier"]

    def __str__(self):
        return f"سطح {self.tier}"
