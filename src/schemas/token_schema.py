from pydantic import BaseModel, Field
from typing import Optional


class TokenVerifyRequest(BaseModel):
    token: str = Field(..., description="JWT access token to verify")


class TokenPayload(BaseModel):
    sub: str
    exp: int
    iat: Optional[int] = None
    provider: Optional[str] = None
    email: Optional[str] = None
    # Add other standard/custom JWT claims as needed


class TokenVerifyResponse(BaseModel):
    valid: bool = Field(..., description="Whether the token is valid")
    payload: Optional[TokenPayload] = Field(
        None, description="Decoded token payload if valid"
    )
