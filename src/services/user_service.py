from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.core.database import async_session
from src.models.user_model import User
from src.models.oauth_model import OAuthAccount
from src.core.security import create_access_token
from src.schemas.user_schema import UserOut


async def handle_oauth_user(user_info: dict, provider: str):
    provider_user_id = user_info.get("sub")
    email = user_info.get("email")
    name = user_info.get("name")
    picture = user_info.get("picture")

    if not email:
        raise ValueError("Email is required from OAuth provider")

    async with async_session() as session:
        # Check if the OAuth account already exists
        result = await session.execute(
            select(OAuthAccount)
            .options(selectinload(OAuthAccount.user))  # eager load the user relationship
            .where(
                OAuthAccount.provider == provider,
                OAuthAccount.provider_user_id == provider_user_id,
            )
        )
        oauth_account = result.scalars().first()

        if oauth_account:
            user = oauth_account.user

        else:
            # Check if a user exists with same email (manual signup or other provider)
            result = await session.execute(
                select(User).where(User.email == email)
            )
            user = result.scalars().first()

            if not user:
                user = User(
                    email=email,
                    full_name=name,
                    profile_picture=picture,
                    is_active=True,
                )
                session.add(user)
                await session.flush()  # Get user.id to use in FK

            # 🔗 Create OAuth mapping
            oauth_account = OAuthAccount(
                provider=provider,
                provider_user_id=provider_user_id,
                user_id=user.id,
            )
            session.add(oauth_account)

            await session.commit()

        # Generate JWT
        token = create_access_token(data={"sub": user.email, "provider": provider})
        return UserOut.model_validate(user), token
