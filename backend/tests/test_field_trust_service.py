import uuid

import pytest

from app.database import AsyncSessionLocal
from app.services import field_trust_service


@pytest.mark.asyncio
async def test_no_signal_returns_none():
    async with AsyncSessionLocal() as db:
        result = await field_trust_service.get_trust_signal(db, f"nonexistent_field_{uuid.uuid4().hex}")
        assert result is None


@pytest.mark.asyncio
async def test_confirmation_increments_confirmed_count():
    async with AsyncSessionLocal() as db:
        try:
            field_name = f"owner_name_{uuid.uuid4().hex}"
            await field_trust_service.record_confirmation(db, field_name)
            await field_trust_service.record_confirmation(db, field_name)
            await db.commit()

            signal = await field_trust_service.get_trust_signal(db, field_name)
            assert signal.confirmed_count == 2
            assert signal.corrected_count == 0
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_correction_increments_corrected_count():
    async with AsyncSessionLocal() as db:
        try:
            field_name = f"valuation_{uuid.uuid4().hex}"
            await field_trust_service.record_correction(db, field_name)
            await db.commit()

            signal = await field_trust_service.get_trust_signal(db, field_name)
            assert signal.confirmed_count == 0
            assert signal.corrected_count == 1
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_confirmations_and_corrections_accumulate_together():
    async with AsyncSessionLocal() as db:
        try:
            field_name = f"survey_no_{uuid.uuid4().hex}"
            await field_trust_service.record_confirmation(db, field_name)
            await field_trust_service.record_confirmation(db, field_name)
            await field_trust_service.record_correction(db, field_name)
            await db.commit()

            signal = await field_trust_service.get_trust_signal(db, field_name)
            assert signal.confirmed_count == 2
            assert signal.corrected_count == 1
        finally:
            await db.rollback()


@pytest.mark.asyncio
async def test_sentinel_field_names_excluded():
    """Tracking a trust signal for _marginalia/_join_mismatch/
    _stitch_ambiguous would be meaningless noise -- these aren't real
    data fields."""
    async with AsyncSessionLocal() as db:
        try:
            for sentinel in ("_marginalia", "_join_mismatch", "_stitch_ambiguous"):
                await field_trust_service.record_confirmation(db, sentinel)
                await field_trust_service.record_correction(db, sentinel)
            await db.commit()

            for sentinel in ("_marginalia", "_join_mismatch", "_stitch_ambiguous"):
                assert await field_trust_service.get_trust_signal(db, sentinel) is None
        finally:
            await db.rollback()
