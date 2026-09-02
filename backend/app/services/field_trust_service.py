"""TS4 — field-shape trust signal. Generalizes TS1's shape-hash caching
pattern ("ask once per kind of ambiguity, reuse for future instances of
that shape") to the fact-verification adjudication queue: informational
only, never bypasses T51/T55's human-confirmation requirement.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field_trust_signal import FieldTrustSignal

# Sentinel field_names that aren't genuine low-confidence data fields —
# tracking a trust signal for these would be meaningless noise.
_EXCLUDED_FIELD_NAMES = {"_marginalia", "_join_mismatch", "_stitch_ambiguous"}


async def get_trust_signal(db: AsyncSession, field_name: str) -> Optional[FieldTrustSignal]:
    if field_name in _EXCLUDED_FIELD_NAMES:
        return None
    return await db.get(FieldTrustSignal, field_name)


async def record_confirmation(db: AsyncSession, field_name: str) -> None:
    if field_name in _EXCLUDED_FIELD_NAMES:
        return
    signal = await db.get(FieldTrustSignal, field_name)
    if signal is None:
        signal = FieldTrustSignal(field_name=field_name, confirmed_count=0, corrected_count=0)
        db.add(signal)
    signal.confirmed_count += 1
    await db.flush()


async def record_correction(db: AsyncSession, field_name: str) -> None:
    if field_name in _EXCLUDED_FIELD_NAMES:
        return
    signal = await db.get(FieldTrustSignal, field_name)
    if signal is None:
        signal = FieldTrustSignal(field_name=field_name, confirmed_count=0, corrected_count=0)
        db.add(signal)
    signal.corrected_count += 1
    await db.flush()
