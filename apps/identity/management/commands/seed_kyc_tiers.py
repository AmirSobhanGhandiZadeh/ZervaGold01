"""
Seed KYC Tier Policies

مرجع: ZRV-ERD-002 بخش ۳.۵ — داده Seed دقیقاً همان سه‌سطحی که در
ZRV-FLOW-001 قفل شد: ۲۰ گرم / ۵۰ گرم / نامحدود.

این Command Idempotent است (طبق ZRV-BOOT-001 بخش ۷۶) — اجرای مکرر آن
رکورد تکراری نمی‌سازد.
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.identity.models import KycTierPolicy

TIERS = [
    {
        "tier": 0,
        "max_grams_per_transaction": Decimal("20"),
        "required_verification": "فقط OTP + تکمیل پروفایل",
        "description_fa": "سطح پایه — بدون Verify رسمی کد ملی",
    },
    {
        "tier": 1,
        "max_grams_per_transaction": Decimal("50"),
        "required_verification": "اتصال به سامانه ثبت‌احوال",
        "description_fa": "Verify کد ملی از طریق ثبت‌احوال",
    },
    {
        "tier": 2,
        # 🧮 طبق ZRV-ERD-002 بخش ۹: سقف نهایی این Tier هنوز TBD است.
        "max_grams_per_transaction": None,
        "required_verification": "اتصال به سامانه بانکی",
        "description_fa": "فعال‌سازی پرداخت درون‌برنامه‌ای — بدون سقف تعریف‌شده فعلی",
    },
]


class Command(BaseCommand):
    help = "Seed کردن سه سطح KYC طبق ZRV-FLOW-001 (idempotent)"

    def handle(self, *args, **options):
        for data in TIERS:
            policy, created = KycTierPolicy.objects.update_or_create(
                tier=data["tier"],
                defaults={
                    "max_grams_per_transaction": data["max_grams_per_transaction"],
                    "required_verification": data["required_verification"],
                    "description_fa": data["description_fa"],
                },
            )
            verb = "ایجاد شد" if created else "به‌روزرسانی شد"
            self.stdout.write(self.style.SUCCESS(f"Tier {policy.tier}: {verb}"))
