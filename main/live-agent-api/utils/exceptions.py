class APIException(Exception):
    """Base API exception"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(self.message)


class UnauthorizedException(APIException):
    """Unauthorized exception (401)"""
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(401, message)


class NotFoundException(APIException):
    """Not found exception (404)"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(404, message)


class BadRequestException(APIException):
    """Bad request exception (400)"""
    def __init__(self, message: str = "Bad request"):
        super().__init__(400, message)


class ForbiddenException(APIException):
    """Forbidden exception (403)"""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(403, message)


class ConflictException(APIException):
    """Conflict exception (409)"""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(409, message)

