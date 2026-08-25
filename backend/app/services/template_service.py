import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template

# D-5 — conservative default for any field that doesn't declare its own
# confidence_bands: a template nobody has calibrated yet should default
# toward "ask a person," not toward "trust it."
DEFAULT_CONFIDENCE_BANDS = {"auto_commit": 0.85, "review_floor": 0.5}


def classify_confidence(field_def: Dict[str, Any], confidence: Optional[float], is_handwritten: bool = False) -> str:
    """D-5 — apply one field's confidence_bands (or the conservative global
    default) to a reported confidence score. Returns 'machine' or
    'in_review' — never 'verified', which only the human promotion step
    (T51) may write.

    No reported confidence at all is treated as the lowest-trust case:
    'in_review', not an auto-commit by default.

    T30 — a handwritten field never auto-commits, no matter how confident
    the model is: "never verified without a human" starts at extraction,
    not just at the confirm step (T55 already enforces the other half —
    bulk_confirm_facts refuses to promote one to 'verified').
    """
    if is_handwritten:
        return "in_review"
    if confidence is None:
        return "in_review"

    bands = field_def.get("confidence_bands") or DEFAULT_CONFIDENCE_BANDS
    auto_commit = bands.get("auto_commit", DEFAULT_CONFIDENCE_BANDS["auto_commit"])
    return "machine" if confidence >= auto_commit else "in_review"


@dataclass
class ValidationError:
    field: str
    reason: str


async def get_template(db: AsyncSession, form_type: str, era_label: str) -> Optional[Template]:
    res = await db.execute(
        select(Template).where(Template.form_type == form_type, Template.era_label == era_label)
    )
    return res.scalar_one_or_none()


async def list_templates(db: AsyncSession, form_type: Optional[str] = None) -> List[Template]:
    stmt = select(Template)
    if form_type:
        stmt = stmt.where(Template.form_type == form_type)
    res = await db.execute(stmt.order_by(Template.form_type, Template.era_label))
    return list(res.scalars().all())


def validate_fields(template: Template, extracted_fields: Dict[str, Any]) -> List[ValidationError]:
    """Check extracted field values against one template's per-field rules.

    Never a single validator for everything — each template's field_schema
    carries its own rules (Section 12: "written per template, never once
    for everything").
    """
    errors: List[ValidationError] = []

    for field_def in template.field_schema:
        name = field_def["name"]
        required = field_def.get("required", False)
        value = extracted_fields.get(name)

        if value is None or value == "":
            if required:
                errors.append(ValidationError(field=name, reason="required field is missing"))
            continue

        field_type = field_def.get("type")
        if field_type == "number":
            if not isinstance(value, (int, float)):
                errors.append(ValidationError(field=name, reason=f"expected a number, got {type(value).__name__}"))
                continue
            min_v = field_def.get("min")
            max_v = field_def.get("max")
            if min_v is not None and value < min_v:
                errors.append(ValidationError(field=name, reason=f"{value} is below minimum {min_v}"))
            if max_v is not None and value > max_v:
                errors.append(ValidationError(field=name, reason=f"{value} is above maximum {max_v}"))

        elif field_type == "string":
            if not isinstance(value, str):
                errors.append(ValidationError(field=name, reason=f"expected a string, got {type(value).__name__}"))
                continue
            pattern = field_def.get("pattern")
            if pattern and not re.match(pattern, value):
                errors.append(ValidationError(field=name, reason=f"'{value}' does not match required pattern {pattern}"))

        allowed_values = field_def.get("allowed_values")
        if allowed_values is not None and value not in allowed_values:
            errors.append(ValidationError(field=name, reason=f"'{value}' is not one of {allowed_values}"))

    return errors
