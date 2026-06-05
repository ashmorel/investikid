from app.core.config import settings


def is_configured() -> bool:
    return all([
        settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key,
        settings.r2_bucket, settings.r2_public_base_url,
    ])


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def public_url(key: str) -> str:
    return f"{settings.r2_public_base_url.rstrip('/')}/{key.lstrip('/')}"


def create_presigned_put(key: str, content_type: str, expires: int = 900) -> str:
    return _client().generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.r2_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=expires,
    )


def delete_object(key: str) -> None:
    _client().delete_object(Bucket=settings.r2_bucket, Key=key)
