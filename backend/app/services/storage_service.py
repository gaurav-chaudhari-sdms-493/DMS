import boto3
import asyncio
import logging
import os
import subprocess
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)


async def convert_to_pdfa(file_bytes: bytes, timeout_seconds: int = 60) -> Optional[bytes]:
    """T41 — mandatory-on-ingest PDF/A-2b rendition, original kept alongside
    (this returns the rendition only; callers decide storage layout).

    Ghostscript is the standard tool for real PDF/A conversion (colour-space
    remapping, font embedding, XMP metadata) — pikepdf/PyPDF2 can only
    *tag* a file as PDF/A without doing that transformation, which would
    be a lie, not a conversion. Returns None (never raises) on any failure
    — a rendition that couldn't be produced must never block ingestion of
    the original, which is still stored and searchable either way.
    """
    def _convert() -> Optional[bytes]:
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = os.path.join(tmpdir, "in.pdf")
            out_path = os.path.join(tmpdir, "out.pdf")
            with open(src_path, "wb") as f:
                f.write(file_bytes)
            try:
                result = subprocess.run(
                    [
                        "gs", "-dPDFA=2", "-dBATCH", "-dNOPAUSE", "-dNOOUTERSAVE",
                        "-dPDFACompatibilityPolicy=1",
                        "-sColorConversionStrategy=RGB",
                        "-sDEVICE=pdfwrite",
                        f"-sOutputFile={out_path}",
                        src_path,
                    ],
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                logger.warning(f"T41 PDF/A conversion unavailable: {e}")
                return None
            if result.returncode != 0 or not os.path.exists(out_path):
                logger.warning(f"T41 PDF/A conversion failed (exit {result.returncode}): {result.stderr.decode(errors='replace')[:500]}")
                return None
            with open(out_path, "rb") as f:
                return f.read()

    return await asyncio.to_thread(_convert)

def _get_s3_client():
    kwargs = {
        'aws_access_key_id': settings.aws_access_key_id,
        'aws_secret_access_key': settings.aws_secret_access_key,
        'region_name': settings.aws_region,
    }
    if settings.s3_endpoint_url:
        kwargs['endpoint_url'] = settings.s3_endpoint_url
    return boto3.client('s3', **kwargs)

async def ensure_bucket_exists():
    def _check():
        client = _get_s3_client()
        try:
            client.head_bucket(Bucket=settings.s3_bucket_name)
        except ClientError:
            try:
                client.create_bucket(Bucket=settings.s3_bucket_name)
                logger.info(f"Created MinIO bucket '{settings.s3_bucket_name}'")
            except Exception as e:
                logger.warning(f"Could not create MinIO bucket: {e}")
    await asyncio.to_thread(_check)

async def upload_file(file_bytes: bytes, s3_key: str, content_type: str) -> str:
    def _upload():
        client = _get_s3_client()
        try:
            client.head_bucket(Bucket=settings.s3_bucket_name)
        except Exception:
            try:
                client.create_bucket(Bucket=settings.s3_bucket_name)
            except Exception:
                pass
        client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type
        )
        return s3_key
    return await asyncio.to_thread(_upload)

async def generate_presigned_url(s3_key: str, expiry_seconds: int = None) -> str:
    if not expiry_seconds:
        expiry_seconds = settings.s3_presigned_url_expiry_seconds
        
    def _generate():
        client = _get_s3_client()
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': settings.s3_bucket_name, 'Key': s3_key},
            ExpiresIn=expiry_seconds
        )
        # Swap internal docker hostname with public endpoint if needed
        if settings.s3_endpoint_url and settings.s3_public_endpoint_url and settings.s3_endpoint_url != settings.s3_public_endpoint_url:
            url = url.replace(settings.s3_endpoint_url, settings.s3_public_endpoint_url)
        return url
    return await asyncio.to_thread(_generate)

async def download_file(s3_key: str) -> bytes:
    def _download():
        client = _get_s3_client()
        response = client.get_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        return response['Body'].read()
    return await asyncio.to_thread(_download)

async def delete_file(s3_key: str) -> None:
    def _delete():
        client = _get_s3_client()
        client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
    await asyncio.to_thread(_delete)


# --- T64: WORM archival storage --------------------------------------------
#
# Object Lock can only be enabled at bucket creation, and requires
# versioning — a bucket created without it can never be retrofitted via the
# S3 API. This uses a dedicated archive bucket (s3_archive_bucket_name),
# separate from the main operational bucket, which already exists without
# lock support. Works identically against MinIO (self-hosted, air-gapped
# profile) and real AWS S3 (SaaS profile) — same S3-compatible API either
# way, per the provider-abstraction approach recorded in T09.

async def ensure_archive_bucket_exists() -> None:
    def _check():
        client = _get_s3_client()
        try:
            client.head_bucket(Bucket=settings.s3_archive_bucket_name)
            return
        except ClientError:
            pass
        client.create_bucket(Bucket=settings.s3_archive_bucket_name, ObjectLockEnabledForBucket=True)
        logger.info(f"Created WORM archive bucket '{settings.s3_archive_bucket_name}' with Object Lock enabled")
    await asyncio.to_thread(_check)


async def archive_file_with_retention(file_bytes: bytes, s3_key: str, content_type: str, retention_days: int) -> dict:
    """Upload a file to the WORM archive bucket and immediately apply a
    COMPLIANCE-mode retention lock — not even the bucket owner/root can
    delete or overwrite it before retain_until, matching what "archival
    storage with retention lock" requires for evidence, not just
    ordinary storage.
    """
    retain_until = datetime.utcnow() + timedelta(days=retention_days)

    def _archive():
        client = _get_s3_client()
        client.put_object(
            Bucket=settings.s3_archive_bucket_name,
            Key=s3_key,
            Body=file_bytes,
            ContentType=content_type,
            ObjectLockMode='COMPLIANCE',
            ObjectLockRetainUntilDate=retain_until,
        )
        version = client.head_object(Bucket=settings.s3_archive_bucket_name, Key=s3_key).get('VersionId')
        return version

    version_id = await asyncio.to_thread(_archive)
    return {"s3_key": s3_key, "version_id": version_id, "retain_until": retain_until, "mode": "COMPLIANCE"}


async def get_object_retention(s3_key: str) -> Optional[dict]:
    def _get():
        client = _get_s3_client()
        try:
            resp = client.get_object_retention(Bucket=settings.s3_archive_bucket_name, Key=s3_key)
            return resp.get('Retention')
        except ClientError:
            return None
    return await asyncio.to_thread(_get)


async def delete_archived_file(s3_key: str) -> None:
    """Only ever succeeds after retain_until has passed — that's the point."""
    def _delete():
        client = _get_s3_client()
        client.delete_object(Bucket=settings.s3_archive_bucket_name, Key=s3_key)
    await asyncio.to_thread(_delete)

