from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .paths import DB_PATH, ensure_data_dirs


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[str] = mapped_column(String(64), default="uploaded")
    # uploaded | processing | review | accepted | needs_info | error
    pdf_filename: Mapped[str] = mapped_column(String(512), default="")
    stp_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    pdf_path: Mapped[str] = mapped_column(String(1024), default="")
    stp_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    efficiency_pct: Mapped[float] = mapped_column(Float, default=85.0)
    takeoff_json: Mapped[str] = mapped_column(Text, default="{}")
    times_json: Mapped[str] = mapped_column(Text, default="{}")
    flags_json: Mapped[str] = mapped_column(Text, default="[]")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    def takeoff(self) -> dict[str, Any]:
        return json.loads(self.takeoff_json or "{}")

    def times(self) -> dict[str, Any]:
        return json.loads(self.times_json or "{}")

    def flags(self) -> list[str]:
        return json.loads(self.flags_json or "[]")

    def set_takeoff(self, data: dict[str, Any]) -> None:
        self.takeoff_json = json.dumps(data)

    def set_times(self, data: dict[str, Any]) -> None:
        self.times_json = json.dumps(data)

    def set_flags(self, flags: list[str]) -> None:
        self.flags_json = json.dumps(flags)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "pdf_filename": self.pdf_filename,
            "stp_filename": self.stp_filename,
            "efficiency_pct": self.efficiency_pct,
            "takeoff": self.takeoff(),
            "times": self.times(),
            "flags": self.flags(),
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


ensure_data_dirs()
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    ensure_data_dirs()
    Base.metadata.create_all(bind=engine)
