"""安全工具：Argon2id 密码哈希、JWT 签发校验、TOTP（管理员 MFA）。"""
import base64
import hashlib
import hmac
import struct
import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt as pyjwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import settings
from app.core.errors import AppError

# PasswordHasher 默认即 Argon2id（argon2-cffi >= 21.x）
_ph = PasswordHasher()


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, plain)
    except (VerifyMismatchError, InvalidHashError, ValueError):
        return False


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_token(
    user_id: uuid.UUID, session_id: uuid.UUID, token_type: str, expires_delta: timedelta
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": token_type,  # access / refresh
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,
    }
    return pyjwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str, expected_type: str) -> dict:
    try:
        payload = pyjwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except pyjwt.ExpiredSignatureError:
        raise AppError("TOKEN_EXPIRED")
    except pyjwt.InvalidTokenError:
        raise AppError("UNAUTHENTICATED")
    if payload.get("typ") != expected_type:
        raise AppError("UNAUTHENTICATED")
    return payload


# ---------------- TOTP（RFC 6238，管理员 MFA）----------------
def _b32decode_lenient(secret: str) -> bytes:
    s = secret.upper().replace(" ", "")
    pad = (8 - len(s) % 8) % 8
    return base64.b32decode(s + "=" * pad)


def totp_code(secret: str, at: int | None = None) -> str:
    t = at if at is not None else int(time.time())
    msg = struct.pack(">Q", t // 30)
    digest = hmac.new(_b32decode_lenient(secret), msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def totp_verify(secret: str, code: str) -> bool:
    now = int(time.time())
    return any(
        hmac.compare_digest(totp_code(secret, now + w * 30), code) for w in (-1, 0, 1)
    )


def verify_mfa(user, code: str) -> bool:
    """MFA 校验。

    【仿真逻辑】用户未绑定真实 TOTP secret 时，接受 settings.MOCK_MFA_CODE
    （默认 123456），便于开发联调；绑定了 secret 则严格按 TOTP 校验。
    生产环境将 MOCK_MFA_CODE 置空即可禁用仿真通道。
    """
    if not user.mfa_secret:
        if not settings.MOCK_MFA_CODE:
            return False
        return bool(code) and hmac.compare_digest(code, settings.MOCK_MFA_CODE)
    return totp_verify(user.mfa_secret, code)
