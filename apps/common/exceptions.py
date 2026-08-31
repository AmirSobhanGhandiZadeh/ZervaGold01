from rest_framework.exceptions import APIException
from rest_framework import status

class BaseAppException(APIException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = 'یک خطای غیرمنتظره رخ داد.'
    default_code = 'server_error'

    def __init__(self, detail=None, code=None, status_code=None):
        if detail:
            self.detail = detail
        if code:
            self.default_code = code
        if status_code:
            self.status_code = status_code
        super().__init__(self.detail, self.code)

class DomainRuleException(BaseAppException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = 'نقض قوانین دامنه.'
    default_code = 'domain_rule_violation'

class ResourceNotFoundException(BaseAppException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = 'منبع یافت نشد.'
    default_code = 'not_found'

class UnauthorizedActionException(BaseAppException):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = 'اجازه انجام این عملیات را ندارید.'
    default_code = 'permission_denied'