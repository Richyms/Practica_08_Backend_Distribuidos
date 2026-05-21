from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class SessionInfoMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.client_ip = request.client.host
        request.state.user_agent = request.headers.get("user-agent", "")
        request.state.accept_language = request.headers.get("accept-language", "")
        response = await call_next(request)
        return response