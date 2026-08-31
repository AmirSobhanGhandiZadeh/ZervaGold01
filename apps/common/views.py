"""Common views for health checks and utilities."""

import logging
from datetime import datetime

from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


def check_database() -> dict:
    """Check database connection."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            return {"status": "healthy", "message": "Database connection OK"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


def check_redis() -> dict:
    """Check Redis connection."""
    try:
        from django.core.cache import cache

        cache.set("_health_check", "ok", timeout=5)
        result = cache.get("_health_check")
        if result == "ok":
            return {"status": "healthy", "message": "Redis connection OK"}
        else:
            return {"status": "unhealthy", "message": "Redis read/write failed"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


def check_celery() -> dict:
    """Check Celery worker status."""
    try:
        from celery import current_app

        inspect = current_app().inspect()
        active_workers = inspect.active() or {}
        if active_workers:
            return {
                "status": "healthy",
                "message": f"Celery workers active: {len(active_workers)}",
                "workers": list(active_workers.keys()),
            }
        else:
            return {
                "status": "degraded",
                "message": "No active Celery workers found",
            }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {"status": "unhealthy", "message": str(e)}


class HealthCheckView(APIView):
    """Health check endpoint for monitoring."""

    authentication_classes = []
    permission_classes = []

    def get(self, request):
        """Return health status of all services."""
        checks = {
            "database": check_database(),
            "redis": check_redis(),
            "celery": check_celery(),
        }

        # Determine overall status
        statuses = [check["status"] for check in checks.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
            status_code = 503
        elif "degraded" in statuses:
            overall_status = "degraded"
            status_code = 200
        else:
            overall_status = "healthy"
            status_code = 200

        # Calculate uptime
        start_time = getattr(settings, "START_TIME", timezone.now())
        uptime = (timezone.now() - start_time).total_seconds()

        response_data = {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": uptime,
            "version": getattr(settings, "VERSION", "unknown"),
            "checks": checks,
        }

        return JsonResponse(response_data, status=status_code)
