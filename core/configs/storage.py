from datetime import timedelta
from fastapi import HTTPException
from minio import Minio, S3Error

from core.configs import settings

endpoint = f"{settings.STORAGE_ENDPOINT}"

client = Minio(
            endpoint,
            access_key=settings.STORAGE_ACCESS_KEY,
            secret_key=settings.STORAGE_SECRET_KEY,
            secure=False # todo setup secure
        )

def make_upload_url(bucket: str, object_name: str, expires: int = 3600) -> str:
    try:
        return client.presigned_put_object(bucket, object_name, expires=timedelta(seconds=expires))
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO upload URL error: {str(e)}")

def get_download_link(bucket: str, object_name: str, expires: int = 3600) -> str:
    try:
        return client.presigned_get_object(bucket, object_name, expires=timedelta(seconds=expires))
    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO download URL error: {str(e)}")

def download_file(bucket: str, object_name: str) -> bytes:
    try:
        response = client.get_object(bucket, object_name)
        data = response.read()
        response.close()
        response.release_conn()
        return data
    except S3Error as e:
        raise HTTPException(status_code=404, detail=f"File not found in MinIO: {str(e)}")