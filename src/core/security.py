import jwt
from datetime import datetime, timedelta, timezone
from typing import Union
from decouple import config

JWT_SECRET_KEY = config("JWT_SECRET_KEY")
JWT_ALGORITHM = config("JWT_ALGORITHM", default="HS256")
JWT_EXPIRATION_DELTA = int(config("JWT_EXPIRATION_MINUTES", default=60))


def create_access_token(
    data: dict,
    expires_delta: Union[timedelta, None] = None
) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_EXPIRATION_DELTA)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
