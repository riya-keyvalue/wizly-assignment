from __future__ import annotations

import uuid

import boto3
import pytest
from moto import mock_aws

from app.services.storage_service import MAX_FILE_SIZE_BYTES, StorageService

BUCKET = "test-bucket"
REGION = "us-east-1"


def _make_client():
    return boto3.client("s3", region_name=REGION)


@pytest.fixture
def s3(aws_credentials):  # noqa: ARG001  — aws_credentials fixture sets dummy env vars
    with mock_aws():
        client = _make_client()
        client.create_bucket(Bucket=BUCKET)
        yield client


@pytest.fixture
def aws_credentials(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", REGION)


@pytest.fixture
def storage(aws_credentials):  # noqa: ARG001
    with mock_aws():
        client = _make_client()
        yield StorageService(s3_client=client, bucket=BUCKET)


def test_save_file_returns_key(storage: StorageService) -> None:
    user_id = uuid.uuid4()
    key = storage.save_file(user_id, "report.pdf", b"fake-pdf-content")
    assert key.startswith(f"{user_id}/")
    assert key.endswith("_report.pdf")


def test_save_file_object_exists_in_s3(storage: StorageService) -> None:
    user_id = uuid.uuid4()
    content = b"%PDF-1.4 fake content"
    key = storage.save_file(user_id, "doc.pdf", content)

    # Retrieve from the mocked S3 and verify bytes match
    obj = storage._client.get_object(Bucket=BUCKET, Key=key)
    assert obj["Body"].read() == content


def test_save_file_collision_prevention(storage: StorageService) -> None:
    user_id = uuid.uuid4()
    key1 = storage.save_file(user_id, "same.pdf", b"a")
    key2 = storage.save_file(user_id, "same.pdf", b"b")
    assert key1 != key2


def test_delete_file_removes_object(storage: StorageService) -> None:
    user_id = uuid.uuid4()
    key = storage.save_file(user_id, "to_delete.pdf", b"data")
    storage.delete_file(key)

    response = storage._client.list_objects_v2(Bucket=BUCKET, Prefix=key)
    assert response.get("KeyCount", 0) == 0


def test_delete_file_nonexistent_does_not_raise(storage: StorageService) -> None:
    storage.delete_file("nonexistent/key.pdf")  # should log warning, not raise


def test_get_presigned_url_returns_string(storage: StorageService) -> None:
    user_id = uuid.uuid4()
    key = storage.save_file(user_id, "file.pdf", b"data")
    url = storage.get_presigned_url(key)
    assert url.startswith("https://") or url.startswith("http://")


def test_ensure_bucket_creates_if_missing() -> None:
    with mock_aws():
        client = _make_client()
        # Do NOT pre-create the bucket — StorageService._ensure_bucket should create it
        svc = StorageService(s3_client=client, bucket="auto-created-bucket")
        response = client.head_bucket(Bucket="auto-created-bucket")
        assert response["ResponseMetadata"]["HTTPStatusCode"] == 200


def test_max_file_size_constant() -> None:
    assert MAX_FILE_SIZE_BYTES == 20 * 1024 * 1024
