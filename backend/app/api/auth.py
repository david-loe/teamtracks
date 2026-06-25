import hmac

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.auth import (
    PLATFORM_ADMIN_COOKIE_NAME,
    create_platform_admin_token,
    require_platform_admin_session,
)
from app.services.login_rate_limit import (
    check_login_allowed,
    record_login_failure,
    reset_login_failures,
)


router = APIRouter(tags=["platform-auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


@router.post("/api/platform/session")
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    rate_limit_key = f"platform:{_client_ip(request)}"
    check_login_allowed(rate_limit_key)
    if not hmac.compare_digest(payload.password, settings.platform_admin_password.get_secret_value()):
        record_login_failure(rate_limit_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    reset_login_failures(rate_limit_key)
    response.set_cookie(
        PLATFORM_ADMIN_COOKIE_NAME,
        create_platform_admin_token(settings),
        max_age=settings.platform_admin_session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@router.get("/api/platform/session", dependencies=[Depends(require_platform_admin_session)])
def session_status() -> dict[str, bool]:
    return {"authenticated": True}


@router.delete("/api/platform/session", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(PLATFORM_ADMIN_COOKIE_NAME, path="/")


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"
