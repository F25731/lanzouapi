from __future__ import annotations


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: int,
        status_code: int,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


class BadRequestError(AppError):
    def __init__(self, message: str = "bad request", code: int = 40000) -> None:
        super().__init__(message, code=code, status_code=400)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "unauthorized", code: int = 40100) -> None:
        super().__init__(message, code=code, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "forbidden", code: int = 40300) -> None:
        super().__init__(message, code=code, status_code=403)


class NotFoundError(AppError):
    def __init__(self, message: str = "not found", code: int = 40400) -> None:
        super().__init__(message, code=code, status_code=404)


class ConflictError(AppError):
    def __init__(self, message: str = "conflict", code: int = 40900) -> None:
        super().__init__(message, code=code, status_code=409)


class RateLimitError(AppError):
    def __init__(
        self,
        message: str = "rate limit exceeded",
        code: int = 42900,
    ) -> None:
        super().__init__(message, code=code, status_code=429)


class UpstreamError(AppError):
    def __init__(self, message: str = "upstream error", code: int = 50200) -> None:
        super().__init__(message, code=code, status_code=502)
