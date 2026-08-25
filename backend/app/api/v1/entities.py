import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import TokenPayload
from ...deps import get_db, require_tenant_access, require_role
from ...services import entity_360_service, entity_graph_service

router = APIRouter(prefix="/entities", tags=["Entities"])


class EntityNodeCreate(BaseModel):
    entity_type: str
    label: str
    attributes: Optional[Dict[str, Any]] = None


@router.post("", status_code=201)
async def create_entity_node_api(
    node_in: EntityNodeCreate,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    node = await entity_graph_service.create_node(
        db, tenant_id, node_in.entity_type, node_in.label, user_id, attributes=node_in.attributes,
    )
    return {"id": str(node.id), "entity_type": node.entity_type, "label": node.label, "attributes": node.attributes}


@router.get("/{node_id}/360")
async def get_entity_360_api(
    node_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_tenant_access),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    return await entity_360_service.get_entity_360_view(db, tenant_id, node_id)


@router.post("/edges/{edge_id}/confirm")
async def confirm_edge_api(
    edge_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    edge = await entity_graph_service.confirm_edge(db, tenant_id, edge_id, user_id)
    return {"edge_id": str(edge.id), "status": edge.status, "verified_by_actor_id": str(edge.verified_by_actor_id)}


@router.post("/edges/{edge_id}/revert")
async def revert_edge_api(
    edge_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    edge = await entity_graph_service.revert_edge(db, tenant_id, edge_id, user_id)
    return {"edge_id": str(edge.id), "status": edge.status}


@router.post("/edges/bulk-confirm")
async def bulk_confirm_edges_api(
    corpus_folder_id: uuid.UUID,
    threshold: float,
    policy_version: str,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    result = await entity_graph_service.bulk_confirm_edges(
        db, tenant_id, corpus_folder_id, threshold, user_id, policy_version,
    )
    return {
        "batch_id": str(result["batch_id"]),
        "confirmed_count": result["confirmed_count"],
        "edge_ids": [str(eid) for eid in result["edge_ids"]],
    }


@router.post("/edges/bulk-revert/{batch_id}")
async def revert_bulk_edge_batch_api(
    batch_id: uuid.UUID,
    current_user: TokenPayload = Depends(require_role('records_officer', 'operator', 'it_admin')),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = uuid.UUID(current_user.tenant_id)
    user_id = uuid.UUID(current_user.sub)
    result = await entity_graph_service.revert_bulk_batch(db, tenant_id, batch_id, user_id)
    return {
        "reverted_count": result["reverted_count"],
        "edge_ids": [str(eid) for eid in result["edge_ids"]],
    }
