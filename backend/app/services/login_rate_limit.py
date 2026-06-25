import threading
import time
from dataclasses import dataclass

from fastapi import HTTPException, status


MAX_FAILURES = 5
FAILURE_WINDOW_SECONDS = 5 * 60
LOCKOUT_SECONDS = 5 * 60


@dataclass
class LoginAttempt:
    failures: list[float]
    locked_until: float | None = None


_attempts: dict[str, LoginAttempt] = {}
_lock = threading.Lock()


def check_login_allowed(key: str, now: float | None = None) -> None:
    current = time.time() if now is None else now
    with _lock:
        attempt = _attempts.get(key)
        if attempt is None:
            return
        if attempt.locked_until is not None and attempt.locked_until > current:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Try again later.",
            )
        _prune(attempt, current)
        if not attempt.failures:
            _attempts.pop(key, None)


def record_login_failure(key: str, now: float | None = None) -> None:
    current = time.time() if now is None else now
    with _lock:
        attempt = _attempts.setdefault(key, LoginAttempt(failures=[]))
        _prune(attempt, current)
        attempt.failures.append(current)
        if len(attempt.failures) >= MAX_FAILURES:
            attempt.locked_until = current + LOCKOUT_SECONDS


def reset_login_failures(key: str) -> None:
    with _lock:
        _attempts.pop(key, None)


def reset_all_login_rate_limits() -> None:
    with _lock:
        _attempts.clear()


def _prune(attempt: LoginAttempt, now: float) -> None:
    cutoff = now - FAILURE_WINDOW_SECONDS
    attempt.failures = [failure for failure in attempt.failures if failure > cutoff]
    if attempt.locked_until is not None and attempt.locked_until <= now:
        attempt.locked_until = None
