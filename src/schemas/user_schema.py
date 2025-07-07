from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    profile_picture: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


class OAuthAccountOut(BaseModel):
    provider: str
    provider_user_id: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    user: UserOut
