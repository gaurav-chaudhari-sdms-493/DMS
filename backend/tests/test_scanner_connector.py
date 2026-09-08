import base64
import datetime
import io
import os
import time
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from PIL import Image
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app
from app.services.scanner_connector import (
    assess_scan_quality,
    poll_scanner_inbox_once,
    process_scanned_bytes,
)


def create_test_tiff_bytes(num_frames: int = 2) -> bytes:
    """Generate multi-page TIFF bytes for testing."""
    images = [
        Image.new("RGB", (200, 200), color=(255, 0, 0) if i == 0 else (0, 255, 0))
        for i in range(num_frames)
    ]
    buf = io.BytesIO()
    images[0].save(buf, format="TIFF", save_all=True, append_images=images[1:])
    return buf.getvalue()


def test_process_scanned_bytes_passthrough():
    raw_jpg = b"\xff\xd8\xff\xe0\x00\x10JFIF sample jpeg"
    proc_bytes, proc_name, proc_mime, raw_orig = process_scanned_bytes(
        raw_jpg, "test.jpg", mime_type="image/jpeg"
    )
    assert proc_bytes == raw_jpg
    assert proc_name == "test.jpg"
    assert proc_mime == "image/jpeg"
    assert raw_orig is None


def test_process_scanned_bytes_tiff_conversion():
    tiff_bytes = create_test_tiff_bytes(num_frames=2)
    proc_bytes, proc_name, proc_mime, raw_orig = process_scanned_bytes(
        tiff_bytes, "register_page.tiff"
    )

    assert proc_name == "register_page_scanned.pdf"
    assert proc_mime == "application/pdf"
    assert proc_bytes.startswith(b"%PDF")
    assert raw_orig == tiff_bytes


@pytest.mark.asyncio
async def test_scan_inbound_unauthorized():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/connectors/scan-inbound",
            json={"raw_scan_b64": "dGVzdA=="},
        )
    assert res.status_code == 401
    assert "Invalid or missing authentication" in res.json()["detail"]


@pytest.mark.asyncio
async def test_scan_inbound_file_too_large():
    max_mb = settings.scanner_max_upload_size_mb
    over_size_headers = {
        "X-Webhook-Secret": settings.scanner_webhook_secret,
        "Content-Length": str((max_mb + 10) * 1024 * 1024),
    }

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            "/api/v1/connectors/scan-inbound",
            headers=over_size_headers,
            json={"raw_scan_b64": "dGVzdA=="},
        )
    assert res.status_code == 413
    assert "File size exceeds maximum allowed limit" in res.json()["detail"]


@pytest.mark.asyncio
async def test_scan_inbound_successful_ingestion():
    scan_b64 = base64.b64encode(b"%PDF-1.4 scanned sample pdf content").decode("utf-8")
    headers = {"X-Webhook-Secret": settings.scanner_webhook_secret}

    payload = {
        "raw_scan_b64": scan_b64,
        "filename": "land_record_001.pdf",
        "scanner_model": "Fujitsu fi-7160",
        "dpi": 300,
        "color_mode": "color",
    }

    mock_resp = AsyncMock()
    mock_resp.document_id = "99999999-8888-7777-6666-555555555555"

    with patch("app.api.v1.scanner_webhook.get_connector_actor") as mock_actor, \
         patch("app.api.v1.scanner_webhook.already_ingested", return_value=False) as mock_dedup, \
         patch("app.api.v1.scanner_webhook.get_or_create_folder_path", return_value="folder-uuid"), \
         patch("app.api.v1.scanner_webhook.ingest_bytes", return_value=mock_resp) as mock_ingest:

        mock_actor.return_value = (uuid.uuid4(), uuid.uuid4())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/connectors/scan-inbound",
                headers=headers,
                json=payload,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["scans_processed"] == 1
        assert body["scans_ingested"] == 1
        assert body["skipped_duplicate"] == 0
        assert len(body["ingested_details"]) == 1
        assert body["ingested_details"][0]["filename"] == "land_record_001.pdf"
        assert body["ingested_details"][0]["scanner_model"] == "Fujitsu fi-7160"


@pytest.mark.asyncio
async def test_scan_inbound_duplicate_detection():
    scan_b64 = base64.b64encode(b"%PDF-1.4 duplicate scanned content").decode("utf-8")
    headers = {"X-Webhook-Secret": settings.scanner_webhook_secret}

    payload = {
        "raw_scan_b64": scan_b64,
        "filename": "existing_scan.pdf",
    }

    with patch("app.api.v1.scanner_webhook.get_connector_actor") as mock_actor, \
         patch("app.api.v1.scanner_webhook.already_ingested", return_value=True) as mock_dedup:

        mock_actor.return_value = (uuid.uuid4(), uuid.uuid4())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/connectors/scan-inbound",
                headers=headers,
                json=payload,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["scans_processed"] == 1
        assert body["scans_ingested"] == 0
        assert body["skipped_duplicate"] == 1


@pytest.mark.asyncio
async def test_poll_scanner_inbox_lifecycle(tmp_path: Path):
    inbox_dir = tmp_path / "scanner_inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    scan_file = inbox_dir / "network_scan_001.pdf"
    scan_file.write_bytes(b"%PDF-1.4 network scanner sample payload")
    
    # Backdate mtime so stability check passes on poll 1
    past_time = time.time() - 20
    os.utime(scan_file, (past_time, past_time))

    mock_resp = AsyncMock()
    mock_resp.document_id = "11223344-5566-7788-9900-aabbccddeeff"

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    with patch.object(settings, "scanner_inbox_dir", str(inbox_dir)), \
         patch("app.services.scanner_connector.STABILITY_GRACE_SECONDS", 0), \
         patch("app.services.scanner_connector.get_connector_actor", return_value=("tenant-1", "user-1")), \
         patch("app.services.scanner_connector.already_ingested", return_value=False), \
         patch("app.services.scanner_connector.get_or_create_folder_path", return_value="folder-1"), \
         patch("app.services.scanner_connector.ingest_bytes", return_value=mock_resp):

        # First poll records pending size, second poll verifies stability and processes
        await poll_scanner_inbox_once()
        count = await poll_scanner_inbox_once()

    assert count == 1
    assert not scan_file.exists()

    expected_processed_file = inbox_dir / "processed" / today_str / "network_scan_001.pdf"
    assert expected_processed_file.exists()


@pytest.mark.asyncio
async def test_poll_scanner_inbox_failure_lifecycle(tmp_path: Path):
    inbox_dir = tmp_path / "scanner_inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    bad_scan_file = inbox_dir / "corrupted_scan.pdf"
    bad_scan_file.write_bytes(b"corrupted scan bytes")

    past_time = time.time() - 20
    os.utime(bad_scan_file, (past_time, past_time))

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    with patch.object(settings, "scanner_inbox_dir", str(inbox_dir)), \
         patch("app.services.scanner_connector.STABILITY_GRACE_SECONDS", 0), \
         patch("app.services.scanner_connector.get_connector_actor", return_value=("tenant-1", "user-1")), \
         patch("app.services.scanner_connector.already_ingested", return_value=False), \
         patch("app.services.scanner_connector.get_or_create_folder_path", return_value="folder-1"), \
         patch("app.services.scanner_connector.ingest_bytes", side_effect=RuntimeError("MinIO upload failure")):

        await poll_scanner_inbox_once()
        count = await poll_scanner_inbox_once()

    assert count == 0
    assert not bad_scan_file.exists()

    expected_failed_file = inbox_dir / "failed" / today_str / "corrupted_scan.pdf"
    assert expected_failed_file.exists()


@pytest.mark.asyncio
async def test_poll_scanner_inbox_partial_file_stability(tmp_path: Path):
    """Verify partial file mid-write handling: file is NOT ingested while size/mtime is actively changing."""
    inbox_dir = tmp_path / "scanner_inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    partial_file = inbox_dir / "writing_scan.pdf"
    partial_file.write_bytes(b"chunk 1")

    mock_resp = AsyncMock()
    mock_resp.document_id = "abc-123"

    with patch.object(settings, "scanner_inbox_dir", str(inbox_dir)), \
         patch("app.services.scanner_connector.STABILITY_GRACE_SECONDS", 5), \
         patch("app.services.scanner_connector.get_connector_actor", return_value=("tenant-1", "user-1")), \
         patch("app.services.scanner_connector.already_ingested", return_value=False), \
         patch("app.services.scanner_connector.get_or_create_folder_path", return_value="folder-1"), \
         patch("app.services.scanner_connector.ingest_bytes", return_value=mock_resp):

        # Poll 1: File first seen, tracked in _pending_sizes, NOT ingested
        count1 = await poll_scanner_inbox_once()
        assert count1 == 0
        assert partial_file.exists()

        # SMB appends second chunk (size changes from 7 bytes -> 14 bytes)
        partial_file.write_bytes(b"chunk 1 chunk 2")

        # Poll 2: Size changed, NOT ingested
        count2 = await poll_scanner_inbox_once()
        assert count2 == 0
        assert partial_file.exists()

        # Backdate mtime & keep size unchanged (write complete)
        past_time = time.time() - 10
        os.utime(partial_file, (past_time, past_time))

        # Poll 3: Size unchanged and mtime grace met -> Ingested!
        count3 = await poll_scanner_inbox_once()
        assert count3 == 1
        assert not partial_file.exists()


def test_assess_scan_quality_sharp_clean_image():
    """Verify sharp, high-resolution, well-lit test image passes quality checks."""
    # Create a high-res document image with sharp black text lines on off-white paper
    img = Image.new("L", (1000, 1000), color=230)
    for y in range(50, 950, 30):
        for x in range(50, 950):
            if (x // 8) % 2 == 0:
                img.putpixel((x, y), 20)

    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    report = assess_scan_quality(buf.getvalue())

    assert report["passed"] is True
    assert report["warnings"] == []
    assert report["resolution"] == (1000, 1000)
    assert report["sharpness_score"] > settings.scanner_min_sharpness_threshold


def test_assess_scan_quality_blurry_image():
    """Verify blurry scan is detected and flagged."""
    # Flat uniform color with zero edge variation (extremely blurry)
    img = Image.new("L", (1000, 1000), color=128)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    report = assess_scan_quality(buf.getvalue())

    assert "blurry" in report["warnings"]
    assert report["passed"] is False


def test_assess_scan_quality_darkened_image():
    """Verify underexposed/dark scan is detected and flagged."""
    # Dark uniform image with pixel mean near 0
    img = Image.new("L", (1000, 1000), color=10)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    report = assess_scan_quality(buf.getvalue())

    assert "underexposed" in report["warnings"]
    assert report["passed"] is False


def test_assess_scan_quality_blank_page():
    """Verify blank uniform page is detected and flagged."""
    # All white image with 0 variance
    img = Image.new("L", (1000, 1000), color=255)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    report = assess_scan_quality(buf.getvalue())

    assert "possible_blank_page" in report["warnings"]
    assert report["passed"] is False


@pytest.mark.asyncio
async def test_scan_quality_flagged_document_still_ingested():
    """Confirm quality-flagged scans are STILL ingested (scans_ingested==1) with quality_flag='needs_review'."""
    # Generate a dark image that triggers quality warnings
    dark_img = Image.new("L", (1000, 1000), color=5)
    buf = io.BytesIO()
    dark_img.save(buf, format="JPEG")
    scan_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    headers = {"X-Webhook-Secret": settings.scanner_webhook_secret}
    payload = {
        "raw_scan_b64": scan_b64,
        "filename": "dark_waqf_register.jpg",
        "scanner_model": "Fujitsu fi-7160",
        "dpi": 300,
    }

    mock_resp = AsyncMock()
    mock_resp.document_id = "11111111-2222-3333-4444-555555555555"

    with patch("app.api.v1.scanner_webhook.get_connector_actor") as mock_actor, \
         patch("app.api.v1.scanner_webhook.already_ingested", return_value=False), \
         patch("app.api.v1.scanner_webhook.get_or_create_folder_path", return_value="folder-uuid"), \
         patch("app.api.v1.scanner_webhook.ingest_bytes", return_value=mock_resp), \
         patch("app.api.v1.scanner_webhook.MetadataItem"):

        mock_actor.return_value = (uuid.uuid4(), uuid.uuid4())

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            res = await ac.post(
                "/api/v1/connectors/scan-inbound",
                headers=headers,
                json=payload,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "success"
        assert body["scans_ingested"] == 1  # Crucial: document was NOT dropped!
        detail = body["ingested_details"][0]
        assert detail["quality_flag"] == "needs_review"
        assert detail["quality_report"]["passed"] is False
        assert "underexposed" in detail["quality_report"]["warnings"]


