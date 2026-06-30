import time

from .storage import TempStorage

_cleanup_interval = 300  # 5 minutes
_last_cleanup = 0.0


class TempCleanupMiddleware:
    """Periodically clean up stale temp directories on incoming requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _last_cleanup
        now = time.time()
        if now - _last_cleanup > _cleanup_interval:
            _last_cleanup = now
            TempStorage.cleanup(max_age_minutes=60)
        return self.get_response(request)
