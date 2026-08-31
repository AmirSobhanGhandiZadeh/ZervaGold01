import logging
from .exceptions import BaseAppException
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)

class ErrorHandlerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, BaseAppException):
            logger.warning(f"Application Error: {exception}", exc_info=False)
            return exception.render()
        
        if isinstance(exception, APIException):
            return exception.render()

        logger.error(f"Unhandled Exception: {exception}", exc_info=True)
        # بازگرداندن خطای عمومی برای جلوگیری از نشت اطلاعات
        from rest_framework.response import Response
        return Response(
            {"detail": "خطای داخلی سرور"}, 
            status=500
        )