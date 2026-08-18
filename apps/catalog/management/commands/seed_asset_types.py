"""
Seed Asset Types

مرجع: ZRV-ERD-002 بخش ۵.۱ — دقیقاً همان جدول Seed سند:
فقط MELTED_GOLD_18K فعال است؛ بقیه Placeholder فاز آینده هستند.

Idempotent است (طبق ZRV-BOOT-001 بخش ۷۶).
"""

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.catalog.models import AssetType

ASSET_TYPES = [
    {
        "code": "MELTED_GOLD_18K",
        "display_name_fa": "آبشده ۱۸ عیار",
        "purity": Decimal("750"),
        "is_active": True,
    },
    {
        "code": "COIN",
        "display_name_fa": "سکه",
        "purity": None,
        "is_active": False,
    },
    {
        "code": "BULLION_BAR",
        "display_name_fa": "شمش",
        "purity": None,
        "is_active": False,
    },
    {
        "code": "ONLINE_GOLD",
        "display_name_fa": "طلای آنلاین",
        "purity": None,
        "is_active": False,
    },
    {
        "code": "USED_JEWELRY",
        "display_name_fa": "طلای دست‌دوم",
        "purity": None,
        "is_active": False,
    },
]


class Command(BaseCommand):
    help = "Seed کردن کاتالوگ انواع دارایی طبق ZRV-ERD-002 بخش ۵.۱ (idempotent)"

    def handle(self, *args, **options):
        for data in ASSET_TYPES:
            asset_type, created = AssetType.objects.update_or_create(
                code=data["code"],
                defaults={
                    "display_name_fa": data["display_name_fa"],
                    "purity": data["purity"],
                    "is_active": data["is_active"],
                },
            )
            verb = "ایجاد شد" if created else "به‌روزرسانی شد"
            flag = "فعال" if asset_type.is_active else "غیرفعال (فاز آینده)"
            self.stdout.write(self.style.SUCCESS(f"{asset_type.code}: {verb} - {flag}"))

        active_count = AssetType.objects.filter(is_active=True).count()
        if active_count != 1:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠ انتظار می‌رفت دقیقاً ۱ نوع دارایی فعال باشد، "
                    f"ولی {active_count} مورد فعال است. طبق ZRV-FLOW-001 "
                    f"بخش ۴.۳ این باید بازبینی شود."
                )
            )
