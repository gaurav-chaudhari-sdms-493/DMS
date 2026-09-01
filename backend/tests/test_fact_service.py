import uuid
import pytest
from app.services.fact_service import create_fact_with_regions


@pytest.mark.asyncio
async def test_no_region_no_save_rule_raises_value_error(mocker):
    """Artifact Section 2 / T04: If a fact has no region, refuse to save it."""
    mock_db = mocker.MagicMock()
    tenant_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Empty regions list
    with pytest.raises(ValueError, match="no region, no save"):
        await create_fact_with_regions(
            db=mock_db,
            tenant_id=tenant_id,
            document_id=doc_id,
            version_id=version_id,
            field_name="survey_number",
            value="121",
            regions=[]
        )

    # Invalid regions list (no page_id or invalid bbox)
    with pytest.raises(ValueError, match="no region, no save"):
        await create_fact_with_regions(
            db=mock_db,
            tenant_id=tenant_id,
            document_id=doc_id,
            version_id=version_id,
            field_name="survey_number",
            value="121",
            regions=[{"x0": None, "y0": None, "x1": None, "y1": None}]
        )
