import uuid
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class IngestionJob(Base):
    """
    Tracks background asynchronous document ingestion jobs,
    including lifecycle status, processing stage, progress percentage,
    and error diagnostics.
    """
    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        sa.ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="queued",
        index=True,
    )  # queued, processing, completed, failed
    stage: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="queued",
    )  # queued, parsing, cleaning, chunking, embedding, indexing, completed, failed
    progress: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )  # 0 to 100 percentage
    chunk_count: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
    )
    error_message: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )

    document = relationship("Document", backref="ingestion_jobs")
