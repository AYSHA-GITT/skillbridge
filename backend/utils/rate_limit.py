"""
Minimal sliding-window rate limiter for sensitive endpoints (login, registration,
public passport links, candidate search).

Counters live in process memory, so limits apply per server process. That is
enough for the single-process deployment SkillBridge uses today; a multi-worker
deployment should move the counters to Redis (or put limits in the reverse proxy).
Disable in tests with app.config['RATELIMIT_ENABLED'] = False.
"""
import threading
import time
from collections import defaultdict, deque
from functools import wraps

from flask import current_app, jsonify, request

_lock = threading.Lock()
_hits = defaultdict(deque)


def _client_ip():
    return request.remote_addr or 'unknown'


def hit(bucket: str, limit: int, window_seconds: int) -> int:
    """Records one hit; returns seconds to wait if the limit is exceeded, else 0."""
    if not current_app.config.get('RATELIMIT_ENABLED', True):
        return 0
    now = time.monotonic()
    with _lock:
        q = _hits[bucket]
        while q and now - q[0] > window_seconds:
            q.popleft()
        if len(q) >= limit:
            return int(window_seconds - (now - q[0])) + 1
        q.append(now)
        return 0


def blocked_for(bucket: str, limit: int, window_seconds: int) -> int:
    """Like hit() but does not record anything: seconds to wait, or 0."""
    if not current_app.config.get('RATELIMIT_ENABLED', True):
        return 0
    now = time.monotonic()
    with _lock:
        q = _hits.get(bucket)
        if not q:
            return 0
        while q and now - q[0] > window_seconds:
            q.popleft()
        return int(window_seconds - (now - q[0])) + 1 if len(q) >= limit else 0


def reset(bucket_prefix: str = '') -> None:
    with _lock:
        for k in [k for k in _hits if k.startswith(bucket_prefix)]:
            del _hits[k]


def too_many(retry_after: int):
    resp = jsonify({'error': 'Too many requests. Please wait and try again.',
                    'retry_after_seconds': retry_after})
    resp.headers['Retry-After'] = str(retry_after)
    return resp, 429


def rate_limited(name: str, limit: int, window_seconds: int, per_user: bool = False):
    """Decorator: `limit` requests per `window_seconds` per client IP (or per logged-in user)."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            key = _client_ip()
            if per_user:
                from flask_login import current_user
                if current_user.is_authenticated:
                    key = f'user:{current_user.id}'
            wait = hit(f'{name}:{key}', limit, window_seconds)
            if wait:
                return too_many(wait)
            return f(*args, **kwargs)
        return wrapper
    return decorator
