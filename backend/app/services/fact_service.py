from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.fact import Fact
from app.models.page import DocumentPage
from app.models.document import Document
from app.services.storage_service import generate_presigned_url


async def get_fact_with_regions(db: AsyncSession, fact_id: UUID, tenant_id: UUID) -> dict:
    """T53 — everything a click-through viewer needs for one fact: its
    regions, each region's page (for rotation/skew/width/height per T06),
    and the source document's presigned URL to render.
    """
    stmt = (
        select(Fact)
        .where(Fact.id == fact_id, Fact.tenant_id == tenant_id)
        .options(selectinload(Fact.regions))
    )
    res = await db.execute(stmt)
    fact = res.scalar_one_or_none()
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")

    doc_res = await db.execute(
        select(Document)
        .where(Document.id == fact.document_id, Document.tenant_id == tenant_id)
        .options(selectinload(Document.versions))
    )
    doc = doc_res.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Source document not found")

    page_ids = {r.page_id for r in fact.regions}
    pages_res = await db.execute(select(DocumentPage).where(DocumentPage.id.in_(page_ids)))
    pages_by_id = {p.id: p for p in pages_res.scalars().all()}

    curr_version = next((v for v in doc.versions if v.id == doc.current_version_id), None)
    download_url = None
    if curr_version and curr_version.s3_path:
        download_url = await generate_presigned_url(curr_version.s3_path)

    regions_out = []
    for region in fact.regions:
        page = pages_by_id.get(region.page_id)
        if not page:
            continue
        regions_out.append({
            "region_id": str(region.id),
            "page_number": page.page_number,
            "page_width": page.width,
            "page_height": page.height,
            "rotation": page.rotation,
            "skew": page.skew,
            "x0": region.x0,
            "y0": region.y0,
            "x1": region.x1,
            "y1": region.y1,
        })

    return {
        "fact_id": str(fact.id),
        "field_name": fact.field_name,
        "value": fact.value,
        "confidence": fact.confidence,
        "status": fact.status,
        "document_id": str(fact.document_id),
        "document_title": doc.title,
        "download_url": download_url,
        "regions": regions_out,
    }


async def create_fact_with_regions(
    db: AsyncSession,
    tenant_id: UUID,
    document_id: UUID,
    version_id: UUID,
    field_name: str,
    value: dict | list | str | float | int,
    regions: list[dict],
    confidence: Optional[float] = None,
    is_handwritten: bool = False,
    status: str = "in_review",
) -> Fact:
    """Enforce Artifact Section 2 / T04 rule: 'If a fact has no region, refuse to save it.'

    Every fact MUST point at the exact spot on the page it came from before being persisted.
    """
    from app.models.fact_region import FactRegion
    from app.utils.bbox import normalize_bbox

    if not regions:
        raise ValueError("Cannot save fact: 'no region, no save' rule requires at least one FactRegion attached.")

    valid_regions = []
    for r in regions:
        bbox = [r.get("x0"), r.get("y0"), r.get("x1"), r.get("y1")]
        norm = normalize_bbox(bbox, r.get("page_width"), r.get("page_height"))
        if norm and r.get("page_id"):
            valid_regions.append((r["page_id"], norm))

    if not valid_regions:
        raise ValueError("Cannot save fact: 'no region, no save' rule requires at least one valid FactRegion attached.")

    fact = Fact(
        tenant_id=tenant_id,
        document_id=document_id,
        version_id=version_id,
        field_name=field_name,
        value=value if isinstance(value, (dict, list)) else {"v": value},
        confidence=confidence,
        is_handwritten=is_handwritten,
        status=status,
    )
    db.add(fact)
    await db.flush()

    for page_id, norm_bbox in valid_regions:
        x0, y0, x1, y1 = norm_bbox
        db.add(
            FactRegion(
                tenant_id=tenant_id,
                fact_id=fact.id,
                page_id=page_id,
                x0=float(x0),
                y0=float(y0),
                x1=float(x1),
                y1=float(y1),
            )
        )

    await db.flush()
    return fact
