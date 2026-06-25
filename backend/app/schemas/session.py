from pydantic import BaseModel, ConfigDict, Field


class SessionOrganizationRead(BaseModel):
    id: int
    name: str
    image_url: str = Field(alias="imageUrl")
    is_admin: bool = Field(alias="isAdmin")

    model_config = ConfigDict(populate_by_name=True)


class BrowserSessionRead(BaseModel):
    authenticated: bool
    organizations: list[SessionOrganizationRead]


class PasswordLoginRequest(BaseModel):
    password: str = Field(min_length=1)
