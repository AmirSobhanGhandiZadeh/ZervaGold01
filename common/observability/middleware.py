"""
Request ID Middleware

مرجع: ZRV-BOOT-001 بخش ۷۱ (Request ID Middleware) و ADR-046
(Structured Logging + Correlation IDs).

هر Request باید یک X-Request-ID داشته باشد؛ اگر Client آن را نفرستاده
باشد، سرور خودش تولید می‌کند. این ID به response header اضافه می‌شود
و برای اتصال به Logging/Audit در دسترس request قرار می‌گیرد.
"""

import uuid

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class RequestIdMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or request_id

        request.request_id = request_id
        request.correlation_id = correlation_id

        response = self.get_response(request)

        response[REQUEST_ID_HEADER] = request_id
        response[CORRELATION_ID_HEADER] = correlation_id
        return response
