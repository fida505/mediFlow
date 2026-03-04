from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.security import verify_token


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ")[1]
            try:
                payload = verify_token(token)
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")
            clinic_id = payload.get("clinic_id")
            request.state.clinic_id = clinic_id
        # else public or onboarding
        response = await call_next(request)
        return response
