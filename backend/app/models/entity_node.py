from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy import ForeignKey, Text
from datetime import datetime
from typing import Any
import uuid

from app.database import Base


class EntityNode(Base):
    """A real-world entity — a person, a property, an office (Section 6, T10).

    Documents and facts are not nodes here: an edge's target can point at
    either another entity or a fact (see EntityEdge.target_type), so the
    graph stays anchored to the existing doc_dg_facts/doc_dg_documents
    tables rather than duplicating them as a second node type.
    """

    __tablename__ = "entity_dg_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. person, property, office
    label: Mapped[str] = mapped_column(Text, nullable=False)
    attributes: Mapped[Any] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
