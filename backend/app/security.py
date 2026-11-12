import hashlib
import hmac
import os
import secrets
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from collections import defaultdict, deque
from threading import Lock
from time import monotonic
from fastapi import HTTPException, Request

COOKIE_NAME = 'candock_session'
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
SESSION_DAYS = 7
_buckets = defaultdict(deque)
_lock = Lock()
_password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=1)


def hash_password(password):
    return _password_hasher.hash(password)


def check_password(password, encoded):
    try:
        return _password_hasher.verify(encoded, password)
    except (VerificationError, InvalidHashError, ValueError, TypeError):
        return False


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def rate_limit(request: Request, category: str, limit: int, seconds: int, identity=None):
    key = (category, identity or (request.client.host if request.client else 'unknown'))
    instant = monotonic()
    with _lock:
        bucket = _buckets[key]
        while bucket and bucket[0] < instant - seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(429, 'Too many requests. Please try again later.', headers={'Retry-After': str(seconds)})
        bucket.append(instant)
        # Bound attacker-controlled keys in this single-worker deployment.
        if len(_buckets) > 10000:
            for old_key in list(_buckets):
                if _buckets[old_key] and _buckets[old_key][-1] < instant - 3600:
                    del _buckets[old_key]
            if len(_buckets) > 12000:
                _buckets.pop(next(iter(_buckets)), None)
