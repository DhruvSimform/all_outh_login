from authlib.integrations.starlette_client import OAuth
from decouple import config

# OAuth setup
oauth = OAuth()

oauth.register(
    name="twitter",  # Changed to lowercase
    client_id=config("X_CLIENT_ID"),
    client_secret=config("X_CLIENT_SECRET"),
    authorize_url="https://twitter.com/i/oauth2/authorize",  # nosec B106
    access_token_url="https://api.twitter.com/2/oauth2/token",  # nosec B106
    client_kwargs={
        "scope": "tweet.read users.read offline.access",
        "token_endpoint_auth_method": "none",  # Important for PKCE
    },
)

twitter = oauth.create_client("twitter")
