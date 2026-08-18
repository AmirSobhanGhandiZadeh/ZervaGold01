# زروا — Zerva Core API

زیرساخت صنعت طلای ایران — MVP0 Backend (Django + DRF)

## اسناد مرجع این Repository

```text
zerva-product-constitution.md          قانون اساسی محصول
ZRV-DATA-001  Domain Model / ERD       (چشم‌انداز بلندمدت)
ZRV-WF-001    Business Workflow
ZRV-API-001   API Contract
ZRV-FLOW-001  User Flow (MVP0)
ZRV-ERD-002   ERD کامل - هم‌راستا با MVP0   ← منبع مستقیم مدل‌های این کد
ZRV-ENG-002   App Boundary / Migration Mapping ← منبع مستقیم ساختار این Repo
```

## معماری

Modular Monolith (Django) روی ۱۰ App مستقل دامنه‌ای:

| App | دامنه |
|---|---|
| `identity` | کاربر، OTP، سطوح KYC |
| `tenancy` | سازمان (طلافروشی/بنکدار/طلاساز)، قرارداد، عضویت |
| `catalog` | نوع دارایی قابل معامله |
| `pricing` | قیمت لحظه‌ای، اجرت اختصاصی هر طلافروشی |
| `inventory` | موجودی سازمانی |
| `rfid` | 🧩 مرز داده‌ای زیرسیستم RFID (سبک، Reference-only) |
| `ledger` | حساب طلای خریدار |
| `consumer` | سفارش خرید/فروش خریدار |
| `b2b_ledger` | حساب باز طلافروش↔بنکدار، درخواست بنکدار↔طلاساز |
| `platform` | Audit، Outbox، Idempotency |

<<<<<<< HEAD
`identity`، `tenancy` و `catalog` در این مرحله کامل پیاده‌سازی شده‌اند (طبق توالی Commit در ZRV-ENG-002)؛ بقیه به‌صورت Skeleton آماده Commitهای بعدی هستند.
=======
فقط `identity` در این مرحله کامل پیاده‌سازی شده (طبق توالی Commit در ZRV-ENG-002)؛ بقیه به‌صورت Skeleton آماده Commitهای بعدی هستند.
>>>>>>> 0dfcb39eefd20b7a97a77192d8c4042942337d0e

## پیش‌نیاز

- Docker + Docker Compose

## راه‌اندازی سریع

```bash
git clone <repo>
cd zerva

cp .env.example .env

docker compose up -d

docker compose exec api python manage.py migrate
docker compose exec api python manage.py seed_kyc_tiers
<<<<<<< HEAD
docker compose exec api python manage.py seed_asset_types
=======
>>>>>>> 0dfcb39eefd20b7a97a77192d8c4042942337d0e

open http://localhost:8000/docs/
```

یا با یک دستور:

```bash
make bootstrap
```

## دستورات توسعه

```bash
make up            # بالا آوردن Stack
make down           # پایین آوردن Stack
make migrate         # اجرای Migration
make seed            # Seed سطوح KYC
make test            # اجرای تست‌ها
make lint             # Ruff Check
make format           # Ruff Format
make check             # Django System Check
make shell              # Django Shell
```

## تست

```bash
make test
```

## API Docs

بعد از بالا آمدن:

- Swagger: `http://localhost:8000/docs/`
- Health Liveness: `http://localhost:8000/health/live`
- Health Readiness: `http://localhost:8000/health/ready`

## اصول کلیدی (خلاصه)

- احراز هویت فقط با OTP — بدون پسورد ثابت، بدون گوگل/اپل.
- یک شماره موبایل = یک اکانت = یک نقش (`account_role` بعد از ایجاد Immutable است).
- Decimal برای هر مقدار مالی/وزنی — استفاده از `float` ممنوع.
- هیچ Import مستقیم بین App‌ها؛ فقط ارجاع رشته‌ای FK.
- `on_delete=PROTECT` پیش‌فرض برای FKهای حیاتی؛ History حذف نمی‌شود.

جزئیات کامل در اسناد مرجع بالا.
