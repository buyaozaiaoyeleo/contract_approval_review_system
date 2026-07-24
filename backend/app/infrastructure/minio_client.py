"""MinIO 客户端封装"""

import asyncio
from datetime import timedelta
from io import BytesIO

from loguru import logger
from minio import Minio
from minio.error import S3Error

from app.core.config import settings


class MinioClient:
    """MinIO 对象存储客户端，提供文件上传/下载/删除/预签名URL

    所有 IO 方法通过 asyncio.to_thread 将同步 minio-py 调用
    放到线程池执行，避免阻塞 FastAPI 事件循环。
    """

    def __init__(self):
        self._client: Minio | None = None

    @property
    def client(self) -> Minio:
        if self._client is None:
            raise RuntimeError("MinIO 客户端未初始化，请先调用 connect()")
        return self._client

    # ==================== 连接管理 ====================

    def connect(self) -> None:
        self._client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY.get_secret_value(),
            secure=settings.MINIO_SECURE,
        )
        logger.info(f"MinIO 客户端已连接 | endpoint={settings.MINIO_ENDPOINT}")

    async def ensure_bucket(self, bucket_name: str | None = None) -> None:
        """确保 Bucket 存在，不存在则自动创建"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _ensure():
            found = self.client.bucket_exists(bucket)
            if not found:
                self.client.make_bucket(bucket)
                logger.info(f"MinIO Bucket 已创建 | bucket={bucket}")
            else:
                logger.debug(f"MinIO Bucket 已存在 | bucket={bucket}")

        await asyncio.to_thread(_ensure)

    # ==================== 上传 ====================

    async def upload(
        self,
        object_name: str,
        data: bytes,
        content_type: str = "application/octet-stream",
        bucket_name: str | None = None,
    ) -> str:
        """上传字节数据到 MinIO"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _upload():
            self.client.put_object(
                bucket_name=bucket,
                object_name=object_name,
                data=BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

        await asyncio.to_thread(_upload)
        logger.debug(f"MinIO 上传成功 | bucket={bucket} | object={object_name} | size={len(data)}")
        return object_name

    async def upload_file(
        self,
        object_name: str,
        file_path: str,
        content_type: str = "application/octet-stream",
        bucket_name: str | None = None,
    ) -> str:
        """上传本地文件到 MinIO"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _upload():
            self.client.fput_object(
                bucket_name=bucket,
                object_name=object_name,
                file_path=file_path,
                content_type=content_type,
            )

        await asyncio.to_thread(_upload)
        logger.debug(f"MinIO 上传文件成功 | bucket={bucket} | object={object_name} | path={file_path}")
        return object_name

    # ==================== 下载 ====================

    async def download(self, object_name: str, bucket_name: str | None = None) -> bytes:
        """从 MinIO 下载文件内容（返回 bytes）"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _download():
            response = self.client.get_object(bucket_name=bucket, object_name=object_name)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()

        return await asyncio.to_thread(_download)

    async def download_to_file(
        self, object_name: str, file_path: str, bucket_name: str | None = None
    ) -> str:
        """从 MinIO 下载文件到本地路径"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _download():
            self.client.fget_object(bucket_name=bucket, object_name=object_name, file_path=file_path)

        await asyncio.to_thread(_download)
        return file_path

    # ==================== 删除与检查 ====================

    async def delete(self, object_name: str, bucket_name: str | None = None) -> bool:
        """删除 MinIO 中的对象"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _delete():
            try:
                self.client.remove_object(bucket_name=bucket, object_name=object_name)
                return True
            except S3Error:
                return False

        return await asyncio.to_thread(_delete)

    async def exists(self, object_name: str, bucket_name: str | None = None) -> bool:
        """检查对象是否存在"""
        bucket = bucket_name or settings.MINIO_BUCKET

        def _exists():
            try:
                self.client.stat_object(bucket_name=bucket, object_name=object_name)
                return True
            except S3Error:
                return False

        return await asyncio.to_thread(_exists)

    # ==================== 预签名 URL ====================

    def get_presigned_url(
        self, object_name: str, expires: int = 3600, bucket_name: str | None = None
    ) -> str:
        """生成预签名下载 URL，默认有效期 1 小时"""
        bucket = bucket_name or settings.MINIO_BUCKET
        return self.client.presigned_get_object(
            bucket_name=bucket, object_name=object_name, expires=timedelta(seconds=expires)
        )

    def close(self) -> None:
        self._client = None
        logger.info("MinIO 客户端已关闭")


minio_client = MinioClient()
