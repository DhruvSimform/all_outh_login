# app/oauth/google.py
from authlib.integrations.starlette_client import OAuth
from decouple import config

oauth = OAuth()

oauth.register(
    name='google',
    client_id=config('GOOGLE_CLIENT_ID'),
    client_secret=config('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

google = oauth.create_client("google")
