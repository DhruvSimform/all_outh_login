from decouple import config
from fastapi import APIRouter, HTTPException, Request

from src.oauth.github import github
from src.oauth.google import google
from src.schemas.user_schema import TokenResponse
from src.services.user_service import handle_oauth_user
from src.utils.logger import get_logger

logger = get_logger("auth_routes")

router = APIRouter()


@router.get("/login/google")
async def login_via_google(request: Request):
    redirect_uri = f"{config('BASE_URL')}/api/v1/auth/callback/google"
    return await google.authorize_redirect(request, redirect_uri)


@router.get("/callback/google", response_model=TokenResponse)
async def google_callback(request: Request):

    try:
        token = await google.authorize_access_token(request)
        logger.debug(f"OAuth token received: {token}")
    except Exception as e:
        logger.error(f"Failed to authorize Google token: {e}")
        raise HTTPException(status_code=500, detail="Google token authorization failed")

    if "userinfo" not in token:
        logger.warning("No userinfo found in OAuth token")
        raise HTTPException(status_code=400, detail="No userinfo in token response")

    try:
        user_info = token["userinfo"]
        logger.debug(f"User-info = {user_info}")
    except Exception as e:
        logger.error(f"Failed to parse user info: {e}")
        raise HTTPException(status_code=500, detail=f"User info parsing failed: {e}")

    # Store or fetch user from DB (based on oauth_accounts table now)
    user, jwt_token = await handle_oauth_user(user_info, provider="google")

    logger.info(f"User {user.email} authenticated via Google")
    return TokenResponse(access_token=jwt_token, user=user)  # Pydantic UserOut model


@router.get("/login/github")
async def login_via_github(request: Request):
    redirect_uri = f"{config('BASE_URL')}/api/v1/auth/callback/github"
    return await github.authorize_redirect(request, redirect_uri)


@router.get("/callback/github", response_model=TokenResponse)
async def github_callback(request: Request):

    try:
        token = await github.authorize_access_token(request)
        logger.debug(f"OAuth token received: {token}")
    except Exception as e:
        logger.error(f"Failed to authorize GitHub token: {e}")
        raise HTTPException(status_code=500, detail="GitHub token authorization failed")

    # Get user info
    try:
        resp = await github.get("user", token=token)
        user_data = resp.json()
        logger.debug(f"User-info = {user_data}")

        # GitHub doesn't always return email in "user"
        if not user_data.get("email"):
            logger.warning(
                "Email not found in GitHub user profile, checking /user/emails"
            )
            email_resp = await github.get("user/emails", token=token)
            emails = email_resp.json()
            logger.debug(f"GitHub user/emails response: {emails}")
            primary_email = next((e["email"] for e in emails if e.get("primary")), None)
            user_data["email"] = primary_email
    except Exception as e:
        logger.error(f"Failed to fetch user info from GitHub: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch GitHub user info: {e}"
        )

    if not user_data.get("email"):
        logger.warning("GitHub account has no accessible email")
        raise HTTPException(
            status_code=400, detail="GitHub account has no email available"
        )

    # Normalize to match expected user_info dict
    user_info = {
        "sub": str(user_data["id"]),
        "email": user_data["email"],
        "name": user_data.get("name") or user_data.get("login"),
        "picture": user_data.get("avatar_url"),
    }

    user, jwt_token = await handle_oauth_user(user_info, provider="github")

    logger.info(f"User {user.email} authenticated via Github")
    return TokenResponse(access_token=jwt_token, user=user)
