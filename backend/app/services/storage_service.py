import os
import boto3
import asyncio
from app.config import settings
import logging

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
LOCAL_STORAGE_DIR = os.getenv("LOCAL_STORAGE_DIR", os.path.join(BACKEND_DIR, "data", "storage"))

from botocore.config import Config

def _get_s3_client():
    kwargs = {
        'service_name': 's3',
        'aws_access_key_id': settings.aws_access_key_id,
        'aws_secret_access_key': settings.aws_secret_access_key,
        'region_name': settings.aws_region,
        'config': Config(connect_timeout=1, read_timeout=1, retries={'max_attempts': 1})
    }
    if settings.s3_endpoint_url:
        kwargs['endpoint_url'] = settings.s3_endpoint_url
    return boto3.client(**kwargs)

async def ensure_bucket_exists() -> None:
    """Ensure the target S3/MinIO bucket exists on application startup or prepare local disk dir."""
    def _ensure():
        try:
            client = _get_s3_client()
            client.head_bucket(Bucket=settings.s3_bucket_name)
        except Exception:
            try:
                client = _get_s3_client()
                client.create_bucket(Bucket=settings.s3_bucket_name)
                logger.info(f"Created S3 bucket '{settings.s3_bucket_name}' automatically.")
            except Exception as create_err:
                logger.warning(f"Could not connect to S3/MinIO bucket '{settings.s3_bucket_name}': {create_err}. Local disk storage fallback enabled at '{LOCAL_STORAGE_DIR}'.")
        
        os.makedirs(LOCAL_STORAGE_DIR, exist_ok=True)

    await asyncio.to_thread(_ensure)

async def upload_file(file_bytes: bytes, s3_key: str, content_type: str) -> str:
    def _upload():
        try:
            client = _get_s3_client()
            client.put_object(
                Bucket=settings.s3_bucket_name,
                Key=s3_key,
                Body=file_bytes,
                ContentType=content_type
            )
            logger.info(f"Successfully uploaded '{s3_key}' to S3/MinIO.")
            return s3_key
        except Exception as e:
            logger.warning(f"S3/MinIO upload failed ({e}). Falling back to local disk storage for key '{s3_key}'.")
            local_file_path = os.path.join(LOCAL_STORAGE_DIR, s3_key)
            os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
            with open(local_file_path, "wb") as f:
                f.write(file_bytes)
            return s3_key

    return await asyncio.to_thread(_upload)

async def generate_presigned_url(s3_key: str, expiry_seconds: int = None) -> str:
    if not expiry_seconds:
        expiry_seconds = settings.s3_presigned_url_expiry_seconds
        
    def _generate():
        try:
            client = _get_s3_client()
            return client.generate_presigned_url(
                'get_object',
                Params={'Bucket': settings.s3_bucket_name, 'Key': s3_key},
                ExpiresIn=expiry_seconds
            )
        except Exception as e:
            logger.warning(f"Failed to generate presigned S3 URL ({e}). Returning local download path.")
            return f"/api/v1/documents/download-local?s3_key={s3_key}"

    return await asyncio.to_thread(_generate)

async def download_file(s3_key: str) -> bytes:
    def _download():
        try:
            client = _get_s3_client()
            response = client.get_object(Bucket=settings.s3_bucket_name, Key=s3_key)
            return response['Body'].read()
        except Exception as e:
            logger.warning(f"S3/MinIO download failed ({e}). Attempting local disk retrieval for key '{s3_key}'.")
            local_file_path = os.path.join(LOCAL_STORAGE_DIR, s3_key)
            if os.path.exists(local_file_path):
                with open(local_file_path, "rb") as f:
                    return f.read()
            raise FileNotFoundError(f"File key '{s3_key}' not found in S3/MinIO or local disk at '{local_file_path}'.")

    return await asyncio.to_thread(_download)

async def delete_file(s3_key: str) -> None:
    def _delete():
        try:
            client = _get_s3_client()
            client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        except Exception as e:
            logger.warning(f"S3/MinIO delete failed ({e}). Attempting local file deletion for key '{s3_key}'.")
        
        local_file_path = os.path.join(LOCAL_STORAGE_DIR, s3_key)
        if os.path.exists(local_file_path):
            try:
                os.remove(local_file_path)
            except Exception as rm_err:
                logger.warning(f"Could not remove local file '{local_file_path}': {rm_err}")

    await asyncio.to_thread(_delete)
