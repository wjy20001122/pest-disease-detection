import time
from typing import Dict, Tuple
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware


class RateLimiter:
    """简单的内存速率限制器（生产环境应使用 Redis）"""

    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.window_size = 60
        self.requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, identifier: str) -> Tuple[bool, int]:
        """
        检查请求是否允许

        Args:
            identifier: 客户端标识符（IP、用户ID等）

        Returns:
            (是否允许, 剩余请求数)
        """
        now = time.time()
        window_start = now - self.window_size

        if identifier in self.requests:
            self.requests[identifier] = [
                t for t in self.requests[identifier] if t > window_start
            ]

        if len(self.requests[identifier]) >= self.requests_per_minute:
            return False, 0

        self.requests[identifier].append(now)
        remaining = self.requests_per_minute - len(self.requests[identifier])
        return True, remaining

    def cleanup(self):
        """清理过期记录"""
        now = time.time()
        window_start = now - self.window_size
        for identifier in list(self.requests.keys()):
            self.requests[identifier] = [
                t for t in self.requests[identifier] if t > window_start
            ]
            if not self.requests[identifier]:
                del self.requests[identifier]


rate_limiter = RateLimiter(requests_per_minute=60)


def get_client_identifier(request: Request) -> str:
    """获取客户端标识符"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_rate_limit(request: Request) -> None:
    """检查速率限制"""
    identifier = get_client_identifier(request)
    allowed, remaining = rate_limiter.is_allowed(identifier)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试"
        )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""

    async def dispatch(self, request: Request, call_next):
        public_paths = ["/api/auth/login", "/api/auth/register", "/docs", "/openapi.json"]

        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        identifier = get_client_identifier(request)
        allowed, remaining = rate_limiter.is_allowed(identifier)

        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "请求过于频繁，请稍后再试"}
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Limit"] = str(rate_limiter.requests_per_minute)
        return response


from starlette.responses import JSONResponse
