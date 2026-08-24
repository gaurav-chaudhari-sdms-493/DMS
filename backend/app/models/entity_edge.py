from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import ForeignKey, Text, Float, Integer, CheckConstraint
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from app.database import Base

if TYPE_CHECKING:
    from app.models.entity_node import EntityNode

# Tier 1: structural  — "Form A page 4 contains this row"
# Tier 2: mention     — "this row names Ramrao Patil"
# Tier 3: identity     — "Ramrao Patil = R. B. Patil, 1998 ferfar"
# Tier 4: legal        — "this sanad transfers survey no. 121/2A"
VALID_TIERS = (1, 2, 3, 4)
VALID_STATUSES = ("machine", "held", "verified")
VALID_TARGET_TYPES = ("entity", "fact")


class EntityEdge(Base):
    """A typed, tiered link in the entity graph (Section 6, T10).

    Target is polymorphic (target_type/target_id) rather than a rigid FK:
    a tier-3 identity edge connects two entities, but a tier-1/2
    structural/mention edge connects an entity to a fact (doc_dg_facts) —
    no separate "document node" duplicate of what doc_dg_facts already is.

    Every edge carries a creating actor OR a policy version (a bulk
    threshold-confirm operation), never neither — that's what makes
    "who/what created this edge" answerable at audit time.
    """

    __tablename__ = "entity_dg_edges"
    __table_args__ = (
        CheckConstraint("tier IN (1,2,3,4)", name="ck_entity_dg_edges_tier"),
        CheckConstraint("status IN ('machine','held','verified')", name="ck_entity_dg_edges_status"),
        CheckConstraint("target_type IN ('entity','fact')", name="ck_entity_dg_edges_target_type"),
        CheckConstraint(
            "created_by_actor_id IS NOT NULL OR created_by_policy_version IS NOT NULL",
            name="ck_entity_dg_edges_creator_present",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("iam_dg_tenants.id"), index=True)

    edge_type: Mapped[str] = mapped_column(Text, nullable=False)  # e.g. "identity_match", "transfers", "names"
    tier: Mapped[int] = mapped_column(Integer, nullable=False)

    source_node_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("entity_dg_nodes.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_node_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("entity_dg_nodes.id", ondelete="CASCADE"), nullable=True)  # set when target_type='entity'
    target_fact_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("doc_dg_facts.id", ondelete="CASCADE"), nullable=True)  # doc_dg_facts.id when target_type='fact'

    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="machine")

    created_by_actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("iam_dg_users.id"), nullable=True)
    created_by_policy_version: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    evidence_fact_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("doc_dg_facts.id", ondelete="SET NULL"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    source_node: Mapped["EntityNode"] = relationship("EntityNode", foreign_keys=[source_node_id])
