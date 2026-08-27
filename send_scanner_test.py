#!/usr/bin/env python3
"""CLI tool simulating a physical hardware scanner or WebTWAIN agent.

Digitizes paper documents directly into the DMS via POST /api/v1/connectors/scan-inbound.

Usage:
    python3 send_scanner_test.py                          # sends a generated sample scan
    python3 send_scanner_test.py path/to/scanned_doc.pdf  # sends a specific file
"""
import base64
import json
import mimetypes
import sys
import urllib.request
from pathlib import Path

# Configurable endpoints and test defaults
API_URL = "http://localhost:8000/api/v1/connectors/scan-inbound"
SECRET_HEADER = "change_me_scanner_secret"


def generate_sample_scanned_image() -> bytes:
    """Generate a sample JPEG image simulating a scanned 7/12 land record page."""
    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (850, 1100), color=(250, 248, 240))
        d = ImageDraw.Draw(img)

        # Draw simulated Waqf / 7/12 register page content
        d.rectangle([40, 40, 810, 1060], outline=(40, 40, 40), width=3)
        d.text((300, 70), "WAQF REGISTER FORM A - SAMPLE SCAN", fill=(0, 0, 0))
        d.line([(50, 110), (800, 110)], fill=(0, 0, 0), width=2)

        # Grid lines & text
        d.text((70, 140), "Survey No: 121/2A", fill=(20, 20, 20))
        d.text((70, 180), "Holder Name: Ramrao Patil", fill=(20, 20, 20))
        d.text((70, 220), "Village: Basmath", fill=(20, 20, 20))
        d.text((70, 260), "Area: 1 Hectare 25 Are", fill=(20, 20, 20))
        d.text((70, 300), "DPI: 300 (Color)", fill=(20, 20, 20))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=90)
        return buf.getvalue()
    except Exception:
        # Fallback raw byte payload
        return b"Simulated Scanned Image Bytes (Fujitsu fi-7160 300DPI)"


def main():
    import time
    file_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    timestamp_str = str(int(time.time()))
    if file_path and file_path.exists():
        filename = file_path.name
        content = file_path.read_bytes()
        print(f"Reading file '{filename}' ({len(content)} bytes)...")
    else:
        filename = f"scanned_waqf_register_{timestamp_str}.jpg"
        content = generate_sample_scanned_image() + f"\nTimestamp: {timestamp_str}".encode("utf-8")
        print(f"Generated sample scan image '{filename}' ({len(content)} bytes)...")

    b64_content = base64.b64encode(content).decode("utf-8")

    payload_data = {
        "raw_scan_b64": b64_content,
        "filename": filename,
        "scanner_model": "Fujitsu fi-7160 Desktop Scanner",
        "dpi": 300,
        "color_mode": "color",
        "operator_notes": "Digitized directly from Waqf paper archive box #14",
    }

    req_json = json.dumps(payload_data).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "X-Webhook-Secret": SECRET_HEADER,
        "X-Scanner-Secret": SECRET_HEADER,
        "X-User-Email": "teamworklax@gmail.com",
    }

    print(f"Posting scan to {API_URL}...")
    req = urllib.request.Request(API_URL, data=req_json, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req) as resp:
            resp_data = resp.read().decode("utf-8")
            print("\nSUCCESS! Scanner Ingestion Response:")
            print(json.dumps(json.loads(resp_data), indent=2))
    except urllib.error.HTTPError as e:
        print(f"\nHTTP Error {e.code}: {e.reason}")
        print(e.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(f"\nCould not connect to server at {API_URL}: {e.reason}")
        print("Ensure the FastAPI backend server is running!")


if __name__ == "__main__":
    main()
