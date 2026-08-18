import pathlib

BASE = pathlib.Path("/home/claude/zerva/apps")

APPS = {
    "tenancy": ("سازمان و عضویت", "Commit 3"),
    "catalog": ("کاتالوگ دارایی", "Commit 4"),
    "pricing": ("قیمت‌گذاری", "Commit 5"),
    "inventory": ("موجودی", "Commit 6"),
    "rfid": ("مرز RFID", "Commit 6"),
    "ledger": ("حساب طلای خریدار", "Commit 7"),
    "consumer": ("سفارش خریدار", "Commit 8"),
    "b2b_ledger": ("حساب باز B2B", "Commit 9"),
    "platform": ("زیرساخت مشترک پلتفرم", "Commit 10"),
}

APPS_CONFIG_TEMPLATE = """from django.apps import AppConfig


class {classname}Config(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.{app}"
    label = "{app}"
    verbose_name = "{label}"
"""

MODELS_TEMPLATE = '''"""
{label}

مرجع: ZRV-ERD-002 / ZRV-ENG-002
این App طبق توالی Commit پیشنهادی در {commit} پر می‌شود.
مدل‌های این App هنوز پیاده‌سازی نشده‌اند — این فایل عمداً خالی نگه داشته
شده تا INSTALLED_APPS بدون خطا Resolve شود و ساختار از روز اول ثابت بماند
(طبق ADR-080: First Production Slice کوچک می‌ماند).
"""

from django.db import models  # noqa: F401
'''

for app, (label, commit) in APPS.items():
    classname = "".join(w.capitalize() for w in app.split("_"))
    app_dir = BASE / app

    for sub in ["migrations", "api", "application", "domain", "infrastructure"]:
        (app_dir / sub).mkdir(parents=True, exist_ok=True)
        (app_dir / sub / "__init__.py").touch()

    (app_dir / "__init__.py").touch()
    (app_dir / "migrations" / "__init__.py").touch()

    (app_dir / "apps.py").write_text(
        APPS_CONFIG_TEMPLATE.format(classname=classname, app=app, label=label)
    )
    (app_dir / "models.py").write_text(
        MODELS_TEMPLATE.format(label=label, commit=commit)
    )

    print(f"scaffolded: {app}")

print("done")
