"""对象存储适配层【仿真：本地磁盘存储】。

生产切换：实现 StorageBackend 的 S3 版本（boto3），并在工厂函数中按
settings.ENV 返回对应实现，业务代码无需改动。
"""
import re
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import AppError

# 允许的图片扩展名与对应魔数（真实内容校验，防伪造后缀）
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": (b"\xff\xd8\xff", (".jpg", ".jpeg")),
    "image/png": (b"\x89PNG\r\n\x1a\n", (".png",)),
    "image/webp": (b"RIFF", (".webp",)),
}


def _detect_image_type(data: bytes, filename: str) -> str | None:
    """按魔数 + 扩展名双重校验真实文件类型。"""
    for mime, (magic, exts) in ALLOWED_IMAGE_TYPES.items():
        if data.startswith(magic):
            if mime == "image/webp" and data[8:12] != b"WEBP":
                continue
            if any(filename.lower().endswith(e) for e in exts):
                return mime
    return None


class StorageBackend:
    """存储后端接口。"""

    def save(self, data: bytes, filename: str) -> str:
        raise NotImplementedError


class LocalStorage(StorageBackend):
    """【仿真实现】本地磁盘存储，返回相对 URL（由静态服务或网关对外暴露）。"""

    def __init__(self, base_dir: str):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, filename: str) -> str:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
        key = f"{uuid.uuid4().hex[:8]}_{safe_name}"
        (self.base / key).write_bytes(data)
        return f"/uploads/{key}"


def get_storage() -> StorageBackend:
    # 【生产环境】在此返回 S3 适配器，例如：
    # if settings.ENV == "prod": return S3Storage(bucket=...)
    return LocalStorage(settings.UPLOAD_DIR)


async def validate_and_read(file: UploadFile) -> tuple[bytes, str]:
    """统一校验：MIME 白名单 + 扩展名 + 真实内容（魔数）+ 大小限制。"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise AppError("FILE_TYPE_INVALID", f"不支持的文件类型: {file.content_type}")
    max_bytes = settings.UPLOAD_MAX_SIZE_MB * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise AppError("FILE_TOO_LARGE", f"文件不能超过 {settings.UPLOAD_MAX_SIZE_MB}MB")
    if _detect_image_type(data, file.filename or "") is None:
        raise AppError("FILE_CONTENT_INVALID", "文件内容与图片格式不符")
    return data, file.filename or "image"
