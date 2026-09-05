from .base import *  # noqa: F401, F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# در CI/Test از دیتابیس ایزوله استفاده می‌شود (طبق ZRV-BOOT-001 بخش ۴۷).
# مقدار پیش‌فرض اینجا صرفاً برای اجرای سریع تست‌های محلی بدون نیاز به
# Postgres در دسترس بودن است؛ CI واقعی باید DATABASE_URL خودش را ست کند.
DATABASES["default"].setdefault("TEST", {})  # noqa: F405
