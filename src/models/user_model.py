from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from src.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    profile_picture = Column(String, nullable=True)

    provider = Column(String, nullable=False)           # 'google', 'github', etc.
    provider_id = Column(String, index=True, nullable=False)  # Unique ID from provider

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "provider_id", name="uq_provider_providerid"),
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} provider={self.provider}>"
