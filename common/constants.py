"""
Global Constants

مرجع: ZRV-ERD-002 بخش ۱.۵ — ضریب تبدیل واحد وزن باید در یک نقطه‌ی واحد
تعریف شود، نه در چند جای پراکنده در Appهای مختلف.

واحد وزن Canonical در کل پلتفرم «گرم» است؛ نمایش پیش‌فرض قیمت طلا در UI
بر مبنای «مثقال» است.
"""

from decimal import ROUND_HALF_UP, Decimal

GRAM_PER_MESGHAL = Decimal("4.3318")


def gram_to_mesghal_price(price_per_gram: Decimal) -> Decimal:
    """
    قیمت هر گرم را به قیمت معادل هر مثقال (برای نمایش) تبدیل می‌کند.

    این تابع باید تنها نقطه‌ی محاسبه‌ی این تبدیل در کل پروژه باشد
    (طبق ZRV-ERD-002 بخش ۱.۵) - نه اینکه در هر App جداگانه بازنویسی شود.
    """
    return (price_per_gram * GRAM_PER_MESGHAL).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
