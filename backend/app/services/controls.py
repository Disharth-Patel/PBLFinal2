from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from sqlalchemy.orm import Session

from app.db import AuditLog


class RateLimiter:
    def __init__(self) -> None:
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str, limit: int, window: int) -> bool:
        now = monotonic()
        with self._lock:
            requests = self._requests[key]
            while requests and now - requests[0] >= window:
                requests.popleft()
            if len(requests) >= limit:
                return False
            requests.append(now)
            return True


rate_limiter = RateLimiter()


def audit(db: Session, user_id: int | None, action: str, resource: str, detail: str = "") -> None:
    db.add(AuditLog(user_id=user_id, action=action, resource=resource, detail=detail))
