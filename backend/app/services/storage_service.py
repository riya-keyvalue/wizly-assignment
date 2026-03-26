from __future__ import annotations

import logging
import uuid

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


class StorageService:
    """S3-backed file storage.  Uses LocalStack in development, real S3 in production.
    The interface (save_file / delete_file) is intentionally filesystem-agnostic so
    swapping to a different backend requires no changes outside this class."""

    def __init__(self, s3_client=None, bucket: str | None = None) -> None:
        self._client = s3_client or boto3.client(
            "s3",
            endpoint_url=settings.aws_endpoint_url,
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_default_region,
            config=boto3.session.Config(signature_version="s3v4"),
        )
        self._bucket = bucket or settings.s3_bucket_name
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("404", "NoSuchBucket"):
                kwargs: dict = {"Bucket": self._bucket}
                if settings.aws_default_region != "us-east-1":
                    kwargs["CreateBucketConfiguration"] = {"LocationConstraint": settings.aws_default_region}
                self._client.create_bucket(**kwargs)
                logger.info(f"Created S3 bucket '{self._bucket}'")
            else:
                raise

    def save_file(self, user_id: uuid.UUID, filename: str, content: bytes) -> str:
        """Upload *content* to S3 and return the object key."""
        key = f"{user_id}/{uuid.uuid4().hex[:8]}_{filename}"
        self._client.put_object(Bucket=self._bucket, Key=key, Body=content)
        logger.info(f"Saved s3://{self._bucket}/{key} ({len(content)} bytes)")
        return key

    def delete_file(self, key: str) -> None:
        """Delete the object identified by *key* from S3."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
            logger.info(f"Deleted s3://{self._bucket}/{key}")
        except ClientError as exc:
            logger.warning(f"Could not delete s3://{self._bucket}/{key}: {exc}")

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Return a pre-signed URL valid for *expires_in* seconds."""
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in,
        )
