from threading import Lock
from time import monotonic

from django.core.cache import caches
from rest_framework.throttling import BaseThrottle

_attempt_lock = Lock()


class LoginAttemptThrottle(BaseThrottle):
    """Limit credential submissions by direct peer in one Django process."""

    limit = 10
    window_seconds = 60

    def allow_request(self, request, view):
        if request.method != "POST":
            return True

        key = f"login:{request.META.get('REMOTE_ADDR', 'unknown')}"
        cache = caches["login_attempts"]
        with _attempt_lock:
            now = monotonic()
            count, deadline = cache.get(key, (0, now + self.window_seconds))
            if now >= deadline:
                count, deadline = 0, now + self.window_seconds
            if count >= self.limit:
                self.retry_after = deadline - now
                return False
            cache.set(key, (count + 1, deadline), timeout=deadline - now)
        return True

    def wait(self):
        return self.retry_after
