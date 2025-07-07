import uvicorn
from decouple import config
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from src.api.v1.auth_routes import router as auth_router
from src.api.v1.token_routes import router as token_router
from src.core.database import Base, engine
from src.utils.logger import get_logger

logger = get_logger(__name__)


app = FastAPI()

# Required for OAuth
app.add_middleware(SessionMiddleware, secret_key=config("SESSION_SECRET_KEY"))

app.include_router(auth_router, prefix="/api/v1/auth")
app.include_router(token_router, prefix="/api/v1/token")


@app.on_event("startup")
async def on_startup() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def main():
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)  # nosec B104


if __name__ == "__main__":
    main()
