"""
Thread-safe Gemini rate limiter & retry helper for free-tier safety (e.g., gemini-3.8-flash).

Controlled via environment variables:
  GEMINI_MODEL=gemini-3.8-flash
  GEMINI_RPM=10   # max requests per minute (0 disables throttling)
"""
from __future__ import annotations

import os
import threading
import time
from typing import Any


class RateLimiter:
    def __init__(self, rpm: float) -> None:
        self.rpm = rpm
        self.min_interval = (60.0 / rpm) if rpm > 0 else 0.0
        self._lock = threading.Lock()
        self._next_allowed = 0.0

    def acquire(self) -> None:
        if self.min_interval <= 0:
            return
        with self._lock:
            now = time.monotonic()
            wait = self._next_allowed - now
            if wait > 0:
                time.sleep(wait)
                now = time.monotonic()
            self._next_allowed = now + self.min_interval


_LIMITER: RateLimiter | None = None
_LIMITER_LOCK = threading.Lock()


def get_gemini_limiter() -> RateLimiter:
    global _LIMITER
    with _LIMITER_LOCK:
        if _LIMITER is None:
            rpm = float(os.getenv("GEMINI_RPM", "10"))
            _LIMITER = RateLimiter(rpm=rpm)
        return _LIMITER


def generate_content_throttled(client: Any, *, model: str, contents: Any, config: Any, max_retries: int = 4) -> Any:
    limiter = get_gemini_limiter()
    delay = 5.0
    for attempt in range(max_retries + 1):
        limiter.acquire()
        try:
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )
        except Exception as e:
            msg = str(e)
            is_rate_limit = "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()
            # Do not retry hard prepayment depletion (402)
            if "402" in msg or not is_rate_limit or attempt == max_retries:
                raise
            time.sleep(delay)
            delay = min(delay * 2, 60.0)
