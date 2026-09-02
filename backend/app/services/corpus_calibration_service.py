from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.corpus_calibration import CorpusCalibration
from app.services.audit_service import log_action


async def calibrate_corpus(
    db: AsyncSession,
    tenant_id: UUID,
    corpus_folder_id: UUID,
    actor_id: UUID,
    sample_size: Optional[int] = None,
    notes: Optional[str] = None,
) -> CorpusCalibration:
    """T59 — certify that a human has validated this corpus's confidence
    scores are meaningful, unlocking bulk_confirm_edges (T57) for it.

    Always requires a real actor — unlike edge creation, a policy/rule
    can never self-certify its own calibration. Re-calibrating (calling
    this again for the same corpus) simply records a fresh attestation;
    the latest one governs.
    """
    if actor_id is None:
        raise ValueError("calibrating a corpus requires an actor — a policy cannot self-certify")

    existing = await db.execute(
        select(CorpusCalibration).where(
            CorpusCalibration.tenant_id == tenant_id,
            CorpusCalibration.corpus_folder_id == corpus_folder_id,
        )
    )
    row = existing.scalar_one_or_none()

    if row:
        row.calibrated_by_actor_id = actor_id
        row.sample_size = sample_size
        row.notes = notes
        from datetime import datetime
        row.calibrated_at = datetime.utcnow()
        calibration = row
    else:
        calibration = CorpusCalibration(
            tenant_id=tenant_id,
            corpus_folder_id=corpus_folder_id,
            calibrated_by_actor_id=actor_id,
            sample_size=sample_size,
            notes=notes,
        )
        db.add(calibration)

    await db.flush()

    await log_action(
        db, actor_id, tenant_id, "corpus.calibrate",
        resource_type="folder", resource_id=corpus_folder_id,
        details={"sample_size": sample_size, "notes": notes},
    )

    return calibration


async def is_corpus_calibrated(db: AsyncSession, tenant_id: UUID, corpus_folder_id: UUID) -> bool:
    res = await db.execute(
        select(CorpusCalibration.id).where(
            CorpusCalibration.tenant_id == tenant_id,
            CorpusCalibration.corpus_folder_id == corpus_folder_id,
        )
    )
    return res.scalar_one_or_none() is not None
