"""
Domain Policies — Consumer

مرجع: ZRV-ENG-001 بخش ۳۹ (Domain Policy جدا از Application Orchestration)

این ماژول فقط تصمیم خالص Business را پاسخ می‌دهد (بدون Side Effect)؛
فراخوانی آن و اجرای اقدام بعدی (رزرو، رد، اطلاع‌رسانی) برعهده Application
Service آینده است - نه این ماژول.
"""

from decimal import Decimal

from apps.identity.models import KycTierPolicy


def evaluate_kyc_limit(kyc_tier: int, requested_grams: Decimal) -> str:
    """
    مرجع: ZRV-FLOW-001 بخش ۴.۲ و بخش ۹ (سؤال ۹) - اگر مبلغ درخواستی از
    سقف سطح KYC فراتر رود، نتیجه FAILED_LIMIT است (رد/تعلیق خودکار +
    پیشنهاد ارتقا سطح)؛ در غیر این صورت PASSED.

    سطحی بدون سقف تعریف‌شده (max_grams_per_transaction = NULL، طبق
    سطح ۲ فعلی) همیشه PASSED برمی‌گرداند.

    مقدار بازگشتی یکی از مقادیر apps.consumer.models.KycCheckResult است.
    """
    try:
        policy = KycTierPolicy.objects.get(tier=kyc_tier)
    except KycTierPolicy.DoesNotExist as exc:
        raise ValueError(f"سیاست KYC برای سطح {kyc_tier} تعریف نشده است.") from exc

    if policy.max_grams_per_transaction is None:
        return "PASSED"

    if requested_grams > policy.max_grams_per_transaction:
        return "FAILED_LIMIT"

    return "PASSED"
