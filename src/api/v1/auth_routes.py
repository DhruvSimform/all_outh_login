from decouple import config
from fastapi import APIRouter, HTTPException, Request

from src.main import logger
from src.oauth.google import google
from src.schemas.user_schema import TokenResponse
from src.services.user_service import handle_google_oauth_user

router = APIRouter()


@router.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = f"{config('BASE_URL')}/api/v1/auth/callback/google"
    return await google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google", response_model=TokenResponse)
async def google_callback(request: Request):
    token = await google.authorize_access_token(request)

    if "userinfo" not in token:
        raise HTTPException(status_code=400, detail="No userinfo in token response")

    try:
        user_info = token["userinfo"]
        logger.debug(f"User-info = {user_info}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"User info parsing failed: {e}")

    # Store or fetch user from DB (based on oauth_accounts table now)
    user, jwt_token = await handle_google_oauth_user(user_info, provider="google")

    return TokenResponse(access_token=jwt_token, user=user)  # Pydantic UserOut model
