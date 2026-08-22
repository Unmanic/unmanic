#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import base64
import datetime
import hashlib
import hmac
import secrets
import time
from typing import Optional

# scrypt work factors. Stored inside each hash so they can be raised later without a migration.
SCRYPT_N = 2 ** 15
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 32
KEY_BYTES = 32
HASH_SCHEME = "scrypt"

# OpenSSL applies a memory ceiling that defaults to 32 MiB, which n=2**15, r=8 exceeds.
# It must be supplied explicitly or hashlib.scrypt raises ValueError on every call.
_MAXMEM_HEADROOM = 2


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int) -> bytes:
    """
    Derive a key from a password using scrypt.

    :param password:
    :param salt:
    :param n:
    :param r:
    :param p:
    :return:
    """
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=KEY_BYTES,
        maxmem=128 * n * r * _MAXMEM_HEADROOM,
    )


def hash_password(password: str) -> str:
    """
    Hash a plaintext password for storage.

    :param password:
    :return:
    """
    salt = secrets.token_bytes(SALT_BYTES)
    derived = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return "{}${}${}${}${}${}".format(
        HASH_SCHEME,
        SCRYPT_N,
        SCRYPT_R,
        SCRYPT_P,
        base64.b64encode(salt).decode("ascii"),
        base64.b64encode(derived).decode("ascii"),
    )


def _decode(encoded: Optional[str]):
    """
    Split a stored hash into its parts, or return None if it is not usable.

    :param encoded:
    :return:
    """
    if not encoded or not isinstance(encoded, str):
        return None
    parts = encoded.split("$")
    if len(parts) != 6 or parts[0] != HASH_SCHEME:
        return None
    try:
        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = base64.b64decode(parts[4], validate=True)
        derived = base64.b64decode(parts[5], validate=True)
    except (ValueError, TypeError):
        return None
    if n < 2 or r < 1 or p < 1 or not salt or not derived:
        return None
    return n, r, p, salt, derived


def verify_password(password: str, encoded: Optional[str]) -> bool:
    """
    Verify a plaintext password against a stored hash.

    Returns False rather than raising for any malformed or unsupported hash.

    :param password:
    :param encoded:
    :return:
    """
    decoded = _decode(encoded)
    if decoded is None or password is None:
        return False
    n, r, p, salt, expected = decoded
    try:
        candidate = _scrypt(password, salt, n, r, p)
    except (ValueError, MemoryError):
        return False
    return hmac.compare_digest(candidate, expected)


def needs_rehash(encoded: Optional[str]) -> bool:
    """
    Return True if a stored hash uses weaker parameters than the current defaults.

    :param encoded:
    :return:
    """
    decoded = _decode(encoded)
    if decoded is None:
        return True
    n, r, p, _salt, _derived = decoded
    return n < SCRYPT_N or r < SCRYPT_R or p < SCRYPT_P


MIN_PASSWORD_LENGTH = 8
MAX_PASSWORD_LENGTH = 128

# Verified Authorization headers, keyed by a keyed digest so the raw header is never held.
# Only successful verifications are cached, so it cannot be filled by an attacker.
_VERIFY_CACHE_TTL_SECONDS = 300
_verify_cache = {}
_process_secret = secrets.token_bytes(32)


def flush_verify_cache() -> None:
    """
    Drop every cached Basic verification. Called whenever credentials change.

    :return:
    """
    global _process_secret
    _verify_cache.clear()
    _process_secret = secrets.token_bytes(32)


def credential_is_configured() -> bool:
    """
    Return True if a local web account exists.

    :return:
    """
    from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials

    return WebAuthCredentials.select().count() > 0


def get_username() -> Optional[str]:
    """
    Return the configured username, or None.

    :return:
    """
    from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials

    row = WebAuthCredentials.select().first()
    return row.username if row else None


def set_credential(username: str, password: str) -> None:
    """
    Create or replace the local web account.

    :param username:
    :param password:
    :return:
    """
    from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials

    if not username or not str(username).strip():
        raise ValueError("A username is required")
    if password is None or len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError("Password must be at least {} characters".format(MIN_PASSWORD_LENGTH))
    if len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password must be no more than {} characters".format(MAX_PASSWORD_LENGTH))

    username = str(username).strip()
    encoded = hash_password(password)
    WebAuthCredentials.delete().execute()
    WebAuthCredentials.create(
        username=username,
        password_hash=encoded,
        created=datetime.datetime.now(),
        updated=datetime.datetime.now(),
    )
    flush_verify_cache()


def clear_credential() -> None:
    """
    Remove the local web account.

    :return:
    """
    from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials

    WebAuthCredentials.delete().execute()
    flush_verify_cache()


def verify_credential(username: str, password: str) -> bool:
    """
    Verify a username and password against the stored account.

    :param username:
    :param password:
    :return:
    """
    from unmanic.libs.unmodels.webauthcredentials import WebAuthCredentials

    row = WebAuthCredentials.select().first()
    if row is None or username is None or password is None:
        return False
    username_matches = hmac.compare_digest(str(username).encode("utf-8"), str(row.username).encode("utf-8"))
    password_matches = verify_password(password, row.password_hash)
    # Both are evaluated unconditionally so the response time does not reveal which half failed.
    if not (username_matches and password_matches):
        return False
    if needs_rehash(row.password_hash):
        row.password_hash = hash_password(password)
        row.save()
        flush_verify_cache()
    return True


def _cache_key(header: str) -> str:
    """
    Derive a cache key from an Authorization header without retaining the header.

    :param header:
    :return:
    """
    return hmac.new(_process_secret, header.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_basic_header(header: Optional[str]) -> bool:
    """
    Verify an HTTP Basic Authorization header, caching successful results.

    Running scrypt on every request would be both a latency cost and an unauthenticated
    CPU exhaustion vector, so a verified header is remembered for a short window.

    :param header:
    :return:
    """
    if not header or not isinstance(header, str):
        return False
    if not header.startswith("Basic "):
        return False

    key = _cache_key(header)
    expires = _verify_cache.get(key)
    now = time.monotonic()
    if expires is not None:
        if expires > now:
            return True
        _verify_cache.pop(key, None)

    try:
        raw = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (ValueError, TypeError, UnicodeDecodeError):
        return False
    if ":" not in raw:
        return False
    username, password = raw.split(":", 1)

    if not verify_credential(username, password):
        return False

    # Re-derive the key: verify_credential may have rotated the process secret via a rehash.
    _verify_cache[_cache_key(header)] = now + _VERIFY_CACHE_TTL_SECONDS
    return True
