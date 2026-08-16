from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from apps.identity.models import (
    KycTierPolicy,
    KycVerificationEvent,
    OtpVerification,
    User,
)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    مرجع: ZRV-ENG-001 بخش ۸۳ (Django Admin مجاز برای Internal Diagnostics
    و Master Data، اما Mutationهای حساس باید از Application Service بگذرند).
    """

    model = User
    ordering = ["-created_at"]
    list_display = [
        "mobile_e164",
        "account_role",
        "kyc_level",
        "status",
        "is_staff",
        "created_at",
    ]
    list_filter = ["account_role", "status", "kyc_level"]
    search_fields = ["mobile_e164", "national_id", "first_name", "last_name"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("mobile_e164", "password")}),
        (
            "پروفایل",
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "national_id",
                    "date_of_birth",
                )
            },
        ),
        (
            "احراز هویت",
            {
                "fields": (
                    "account_role",
                    "kyc_level",
                    "national_id_verified",
                    "national_id_verified_at",
                    "bank_verified",
                    "bank_verified_at",
                )
            },
        ),
        ("وضعیت", {"fields": ("status", "is_active", "is_staff", "is_superuser")}),
        ("Meta", {"fields": ("id", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("mobile_e164", "account_role", "password1", "password2"),
            },
        ),
    )


@admin.register(OtpVerification)
class OtpVerificationAdmin(admin.ModelAdmin):
    list_display = [
        "mobile_e164",
        "purpose",
        "attempt_count",
        "expires_at",
        "verified_at",
    ]
    list_filter = ["purpose"]
    search_fields = ["mobile_e164"]
    readonly_fields = [f.name for f in OtpVerification._meta.fields]


@admin.register(KycVerificationEvent)
class KycVerificationEventAdmin(admin.ModelAdmin):
    list_display = ["user", "requested_level", "provider", "result", "requested_at"]
    list_filter = ["provider", "result", "requested_level"]
    readonly_fields = [f.name for f in KycVerificationEvent._meta.fields]


@admin.register(KycTierPolicy)
class KycTierPolicyAdmin(admin.ModelAdmin):
    list_display = ["tier", "max_grams_per_transaction", "required_verification"]
