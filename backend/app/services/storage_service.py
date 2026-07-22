import boto3
import asyncio
import logging
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)

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

