import base64
import hashlib
import secrets
import urllib.parse

import aiohttp
from decouple import config
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

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


# In-memory store for PKCE code_verifiers, keyed by state
pkce_store = {}


def generate_pkce_pair():
    """Generate PKCE code verifier and challenge pair"""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode()).digest())
        .rstrip(b"=")
        .decode()
    )
    return code_verifier, code_challenge


@router.get("/login/x")
async def login_via_x():
    """Initiate X (Twitter) OAuth login"""
    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = generate_pkce_pair()

    # Store the code_verifier for later use
    pkce_store[state] = code_verifier

    # Log for debugging
    logger.debug(f"Generated state: {state}")
    logger.debug(f"Code verifier length: {len(code_verifier)}")
    logger.debug(f"Code challenge: {code_challenge}")

    redirect_uri = f"{config('BASE_URL')}/api/v1/auth/callback/x"

    # OAuth parameters
    params = {
        "response_type": "code",
        "client_id": config("X_CLIENT_ID"),
        "redirect_uri": redirect_uri,
        "scope": "tweet.read users.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    # Properly URL encode the parameters
    query_params = urllib.parse.urlencode(params)
    authorize_url = f"https://twitter.com/i/oauth2/authorize?{query_params}"

    logger.debug(f"Redirect URI: {redirect_uri}")
    logger.debug(f"Authorize URL: {authorize_url}")

    return RedirectResponse(authorize_url)


@router.get("/callback/x")  # Remove response_model for now to avoid import issues
async def x_callback(request: Request):
    """Handle X (Twitter) OAuth callback"""
    state = request.query_params.get("state")
    code = request.query_params.get("code")
    error = request.query_params.get("error")

    # Check for OAuth errors first
    if error:
        logger.error(f"OAuth error: {error}")
        error_description = request.query_params.get("error_description", "")
        raise HTTPException(
            status_code=400, detail=f"OAuth error: {error} - {error_description}"
        )

    if not state or not code:
        logger.error(f"Missing parameters - state: {bool(state)}, code: {bool(code)}")
        raise HTTPException(status_code=400, detail="Missing state or code")

    # Retrieve and remove the code_verifier
    code_verifier = pkce_store.pop(state, None)
    if not code_verifier:
        logger.error(f"Missing or invalid PKCE code_verifier for state: {state}")
        logger.error(f"Available states in store: {list(pkce_store.keys())}")
        raise HTTPException(status_code=400, detail="Invalid PKCE flow")

    redirect_uri = f"{config('BASE_URL')}/api/v1/auth/callback/x"

    logger.debug(f"Using code_verifier: {code_verifier}")
    logger.debug(f"Using redirect_uri: {redirect_uri}")

    # Exchange authorization code for access token
    try:
        async with aiohttp.ClientSession() as session:
            token_data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
                "code_verifier": code_verifier,
                "client_id": config("X_CLIENT_ID"),
            }

            # For Twitter OAuth 2.0 with PKCE, try with Basic auth first
            client_id = config("X_CLIENT_ID")
            client_secret = config("X_CLIENT_SECRET", default="")

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            # If client_secret is provided, use Basic auth
            if client_secret:
                credentials = f"{client_id}:{client_secret}"
                encoded_credentials = base64.b64encode(credentials.encode()).decode()
                headers["Authorization"] = f"Basic {encoded_credentials}"
            else:
                # For public clients (PKCE-only), no auth header needed
                logger.debug("Using public client configuration (no client_secret)")

            logger.debug(f"Token request data: {token_data}")
            logger.debug(f"Headers: {headers}")

            async with session.post(
                "https://api.twitter.com/2/oauth2/token",
                data=token_data,
                headers=headers,
            ) as response:
                response_text = await response.text()
                logger.debug(f"Token response status: {response.status}")
                logger.debug(f"Token response: {response_text}")

                if response.status != 200:
                    logger.error(
                        f"Token request failed with status {response.status}: {response_text}"
                    )
                    raise HTTPException(
                        status_code=500, detail=f"Token request failed: {response_text}"
                    )

                token = await response.json()
                logger.debug(f"OAuth token received: {token}")

    except aiohttp.ClientError as e:
        logger.error(f"Network error during token exchange: {e}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to authorize X token: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise HTTPException(
            status_code=500, detail=f"X token authorization failed: {str(e)}"
        )

    # Fetch user info using the access token
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {token['access_token']}",
                "Content-Type": "application/json",
            }

            async with session.get(
                "https://api.twitter.com/2/users/me?user.fields=profile_image_url",
                headers=headers,
            ) as response:
                response_text = await response.text()
                logger.debug(f"User info response status: {response.status}")
                logger.debug(f"User info response: {response_text}")

                if response.status != 200:
                    logger.error(
                        f"User info request failed with status {response.status}: {response_text}"
                    )
                    raise HTTPException(
                        status_code=500,
                        detail=f"User info request failed: {response_text}",
                    )

                user_data = await response.json()
                user_info = user_data.get("data")
                logger.debug(f"Twitter user info: {user_info}")

    except aiohttp.ClientError as e:
        logger.error(f"Network error during user info fetch: {e}")
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to fetch user info from Twitter: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user info from X")

    if not user_info or "id" not in user_info:
        logger.error(f"Invalid user info received: {user_info}")
        raise HTTPException(status_code=400, detail="Invalid user info from X")

    twitter_user_data = {
        "sub": user_info["id"],
        "name": user_info.get("name", ""),
        "username": user_info.get("username", ""),
        "email": None,  # Twitter OAuth 2.0 doesn't provide email,
        "picture": user_info.get("profile_image_url", ""),
        "provider": "x",
    }

    logger.debug(f"Processed Twitter user data: {twitter_user_data}")

    # return twitter_user_data

    # Handle OAuth user (modify this function to handle missing email)
    user, jwt_token = await handle_oauth_user(twitter_user_data, provider="x")

    logger.info(f"User {user.full_name} {user.id} authenticated via X")

    # Return the token response (adjust according to your TokenResponse model)

    return TokenResponse(access_token=jwt_token, user=user)
