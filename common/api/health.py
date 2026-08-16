"""
Health Endpoints

مرجع: ZRV-BOOT-001 بخش ۳۶ (Liveness) و ۳۷ (Readiness).

/health/live   -> فقط تایید می‌کند Process زنده است (بدون هیچ Dependency Check).
/health/ready  -> Dependencyهای حیاتی (Postgres, Redis) را چک می‌کند.
"""

from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse


def live(request):
    return JsonResponse({"status": "ok"})


def ready(request):
    checks = {}
    healthy = True

    try:
        connections["default"].cursor()
        checks["database"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"error: {exc}"
        healthy = False

    try:
        cache.set("health_check", "1", timeout=5)
        cache.get("health_check")
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc}"
        healthy = False

    status_code = 200 if healthy else 503
    return JsonResponse(
        {"status": "ok" if healthy else "degraded", "checks": checks},
        status=status_code,
    )
