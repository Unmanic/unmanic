#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Copyright (C) Josh Sunnex

SPDX-License-Identifier: GPL-3.0-only
"""

import base64
import hashlib
import hmac
import secrets
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
