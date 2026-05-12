import boto3
from botocore.config import Config
from django.conf import settings


def get_r2_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.CLOUDFLARE_R2_ENDPOINT_URL,
        aws_access_key_id=settings.CLOUDFLARE_R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.CLOUDFLARE_R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def generate_presigned_upload_url(key, content_type, expires_in=None):
    client = get_r2_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.CLOUDFLARE_R2_BUCKET_NAME, "Key": key, "ContentType": content_type},
        ExpiresIn=expires_in or settings.R2_SIGNED_URL_EXPIRES_SECONDS,
    )


def generate_presigned_download_url(key, filename=None, expires_in=None):
    params = {"Bucket": settings.CLOUDFLARE_R2_BUCKET_NAME, "Key": key}
    if filename:
        params["ResponseContentDisposition"] = f'attachment; filename="{filename}"'
    return get_r2_client().generate_presigned_url(
        "get_object", Params=params, ExpiresIn=expires_in or settings.R2_SIGNED_URL_EXPIRES_SECONDS
    )


def object_exists(key):
    try:
        get_r2_client().head_object(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=key)
        return True
    except Exception:
        return False


def delete_object(key):
    return get_r2_client().delete_object(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=key)


def copy_object(source_key, destination_key):
    return get_r2_client().copy_object(
        Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME,
        Key=destination_key,
        CopySource={"Bucket": settings.CLOUDFLARE_R2_BUCKET_NAME, "Key": source_key},
    )


def get_object_metadata(key):
    return get_r2_client().head_object(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=key)


def upload_bytes(key, body, content_type):
    return get_r2_client().put_object(
        Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=key, Body=body, ContentType=content_type
    )


def download_bytes(key):
    obj = get_r2_client().get_object(Bucket=settings.CLOUDFLARE_R2_BUCKET_NAME, Key=key)
    return obj["Body"].read()


def build_original_key(user_id, collection_id, media_id, ext):
    return f"users/{user_id}/collections/{collection_id}/originals/{media_id}.{ext}"


def build_preview_key(user_id, collection_id, media_id):
    return f"users/{user_id}/collections/{collection_id}/previews/{media_id}.webp"


def build_thumbnail_key(user_id, collection_id, media_id):
    return f"users/{user_id}/collections/{collection_id}/thumbnails/{media_id}.webp"


def build_export_key(user_id, collection_id, download_job_id):
    return f"users/{user_id}/collections/{collection_id}/exports/{download_job_id}.zip"
