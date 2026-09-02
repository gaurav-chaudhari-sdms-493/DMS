from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Any, Dict, List, Optional


class TemplateFieldDef(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    role: Optional[str] = None
    ditto_eligible: Optional[bool] = None


class TemplateCreate(BaseModel):
    form_type: str
    era_label: str
    field_schema: List[Dict[str, Any]]
    layout: str = "single_page"


class TemplateUpdate(BaseModel):
    form_type: Optional[str] = None
    era_label: Optional[str] = None
    field_schema: Optional[List[Dict[str, Any]]] = None
    layout: Optional[str] = None


class TemplateResponse(BaseModel):
    id: UUID
    form_type: str
    era_label: str
    field_schema: List[Dict[str, Any]]
    layout: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
