import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    messages: Mapped[list] = mapped_column(
        ARRAY(JSONB), default=list, server_default=text("ARRAY[]::jsonb[]")
    )
    agent_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    actions_taken: Mapped[list] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
