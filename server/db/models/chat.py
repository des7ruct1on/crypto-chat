import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import String, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

class ChatStatus(str, enum.Enum):
    waiting = "waiting"
    active = "active"
    secure = "secure"

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    creator_id: Mapped[str]
    algorithm: Mapped[str]
    encryption_mode: Mapped[str]
    padding_mode: Mapped[str]
    status: Mapped[ChatStatus] = mapped_column(default=ChatStatus.waiting)
    p: Mapped[int] = mapped_column(Numeric)
    g: Mapped[int] = mapped_column(Numeric)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="chat", cascade="all, delete-orphan"
    )

class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(ForeignKey("chats.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    public_key: Mapped[Optional[int]] = mapped_column(Numeric, nullable=True)

    chat: Mapped["Chat"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship(back_populates="participants")
