from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Result(Base):
    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    image_id: Mapped[int] = mapped_column(ForeignKey("images.id"), unique=True, nullable=False)

    panel_count: Mapped[int] = mapped_column(Integer, nullable=False)
    detected_area_m2: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_kwh_month: Mapped[float] = mapped_column(Float, nullable=False)
    mask_filepath: Mapped[str | None] = mapped_column(String(500), nullable=True)
    panels: Mapped[list | None] = mapped_column(JSON, nullable=True)

    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    image: Mapped["Image"] = relationship("Image", back_populates="result")
