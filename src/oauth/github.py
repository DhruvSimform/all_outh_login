# app/oauth/github.py
from authlib.integrations.starlette_client import OAuth
from decouple import config

oauth = OAuth()

oauth.register(
    name="github",
    client_id=config("GITHUB_CLIENT_ID"),
    client_secret=config("GITHUB_CLIENT_SECRET"),
    access_token_url="https://github.com/login/oauth/access_token",  # nosec B106
    authorize_url="https://github.com/login/oauth/authorize",  # nosec B106
    api_base_url="https://api.github.com/",  # nosec B106
    client_kwargs={"scope": "user:email"},  # nosec B106
)

github = oauth.create_client("github")
