import uuid

from sqlalchemy import Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.core.database import Base


class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)  # e.g., 'google'
    provider_user_id = Column(String, nullable=False)  # e.g., '10131463...'
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint(
            "provider", "provider_user_id", name="uq_provider_provider_user"
        ),
    )

    def __repr__(self):
        return f"<OAuthAccount provider={self.provider} provider_user_id={self.provider_user_id}>"
