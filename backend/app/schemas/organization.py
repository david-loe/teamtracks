from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.session import BrowserSessionRead


class OrganizationPublicRead(BaseModel):
    id: int
    name: str
    image_url: str = Field(alias="imageUrl")

    model_config = ConfigDict(populate_by_name=True)


class OrganizationAdminRead(OrganizationPublicRead):
    invite_token: str = Field(alias="inviteToken")
    invite_url: str = Field(alias="inviteUrl")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class PasswordChangeRequest(BaseModel):
    new_password: str = Field(alias="newPassword", min_length=8, max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class AdminPasswordChangeRequest(PasswordChangeRequest):
    current_password: str = Field(alias="currentPassword", min_length=1, max_length=512)


class OrganizationDeleteRequest(BaseModel):
    admin_password: str = Field(alias="adminPassword", min_length=1, max_length=512)

    model_config = ConfigDict(populate_by_name=True)


class InviteAcceptRead(BaseModel):
    organization_id: int = Field(alias="organizationId")
    session: BrowserSessionRead

    model_config = ConfigDict(populate_by_name=True)
