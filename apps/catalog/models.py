"""
Catalog App

مرجع: ZRV-ERD-002 بخش ۵.۱ (دامنه کاتالوگ و قیمت‌گذاری - AssetType)

قانون کلیدی طبق ZRV-FLOW-001: نوع دارایی در MVP0 ثابت است (فقط آبشده
۱۸ عیار). این جدول عمداً همه‌ی انواع آینده (سکه، شمش، طلای آنلاین،
دست‌دوم) را از همین الان به‌عنوان رکورد غیرفعال نگه می‌دارد تا UI بتواند
یک Selector کامل نمایش دهد که فقط یک گزینه‌اش فعال است - دقیقاً همان
Node غیرفعالی که در فلوچارت خریدار توصیف شد.
"""

import uuid

from django.db import models


class AssetType(models.Model):
    """مرجع: ZRV-ERD-002 بخش ۵.۱ / جدول `asset_types`"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(max_length=32, unique=True)
    display_name_fa = models.CharField(max_length=100)
    purity = models.DecimalField(max_digits=6, decimal_places=3, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "catalog"
        db_table = "asset_types"
        ordering = ["code"]

    def __str__(self):
        flag = "✓" if self.is_active else "✗"
        return f"{self.display_name_fa} [{flag}]"
