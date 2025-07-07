import jwt
from jwt import PyJWTError

from fastapi import APIRouter

from src.core.security import JWT_SECRET_KEY, JWT_ALGORITHM
from src.schemas.token_schema import TokenVerifyRequest, TokenVerifyResponse


router = APIRouter()


@router.post("/verify-token", response_model=TokenVerifyResponse)
def verify_token(data: TokenVerifyRequest):
    try:
        payload = jwt.decode(data.token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return {"valid": True, "payload": payload}
    except PyJWTError as e:
        print(f"Token verification error: {e}")  # You can replace with logger
        return {"valid": False, "payload": None}
