"""
Seed Pricing Providers

مرجع: roadmap-super-app-tala.md و zerva-business-plan.md — BrsApi.ir
به‌عنوان منبع اصلی و TGJU webservice به‌عنوان Fallback در تمام اسناد
پروژه ذکر شده‌اند. priority پایین‌تر یعنی اولویت بالاتر.

Idempotent است (طبق ZRV-BOOT-001 بخش ۷۶). خودِ Adapterهای واقعی این
Providerها بعداً در Sprint Pricing Integration نوشته می‌شوند - این
Command فقط رکورد Provider را آماده می‌کند.
"""

from django.core.management.base import BaseCommand

from apps.pricing.models import PricingProvider, ProviderStatus

PROVIDERS = [
    {
        "code": "BRSAPI",
        "name": "BrsApi.ir",
        "priority": 1,
        "status": ProviderStatus.ACTIVE,
    },
    {
        "code": "TGJU",
        "name": "TGJU (tgju.org webservice)",
        "priority": 2,
        "status": ProviderStatus.ACTIVE,
    },
]


class Command(BaseCommand):
    help = "Seed کردن Providerهای قیمت (BrsApi اصلی / TGJU Fallback) - idempotent"

    def handle(self, *args, **options):
        for data in PROVIDERS:
            provider, created = PricingProvider.objects.update_or_create(
                code=data["code"],
                defaults={
                    "name": data["name"],
                    "priority": data["priority"],
                    "status": data["status"],
                },
            )
            verb = "ایجاد شد" if created else "به‌روزرسانی شد"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{provider.code}: {verb} (priority={provider.priority})"
                )
            )
