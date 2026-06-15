import hmac

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from app.config import Settings, get_settings
from app.services.auth import ADMIN_COOKIE_NAME, create_admin_token, require_admin_session


router = APIRouter(prefix="/api/admin/session", tags=["admin-auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1)


@router.post("")
def login(payload: LoginRequest, response: Response, settings: Settings = Depends(get_settings)) -> dict[str, bool]:
    if not hmac.compare_digest(payload.password, settings.admin_password.get_secret_value()):
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"authenticated": False}
    response.set_cookie(
        ADMIN_COOKIE_NAME,
        create_admin_token(settings),
        max_age=settings.admin_session_hours * 3600,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@router.get("", dependencies=[Depends(require_admin_session)])
def session_status() -> dict[str, bool]:
    return {"authenticated": True}


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")
