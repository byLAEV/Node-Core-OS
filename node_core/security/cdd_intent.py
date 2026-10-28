"""Experimental CDD intent lobby: opaque, short-lived, single-use access tickets.

This module is a local MVP, not proof that a requester is human. Tickets are
random opaque handles stored server-side; CID and destination metadata are never
embedded in the handle or returned to the requester. A future distributed
implementation must replicate ticket state and consume-once semantics safely.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import secrets
import threading
import time
from typing import Callable, Mapping


MAX_INTENT_LENGTH = 128
MAX_DESTINATION_ID_LENGTH = 256
MAX_TICKET_TTL_SECONDS = 900
MAX_MIN_WAIT_SECONDS = 120
MAX_ACTIVE_TICKETS = 100_000


class CDDIntentError(ValueError):
    """Raised when an intent ticket is invalid, expired, replayed, or too early."""


@dataclass(frozen=True)
class IntentRoute:
    """Operator-approved intent route; destination_id is an internal registry key."""

    destination_id: str
    content_cid: str


@dataclass(frozen=True)
class IntentGrant:
    """Server-side result of consuming a ticket; do not serialize directly to clients."""

    intent: str
    destination_id: str
    content_cid: str
    issued_at: float
    expires_at: float


@dataclass(frozen=True)
class _Ticket:
    digest: bytes
    intent: str
    destination_id: str
    content_cid: str
    issued_at: float
    expires_at: float
    min_wait_seconds: int
    consumed: bool = False


class CDDIntentLobby:
    """Bounded local lobby that issues opaque handles and consumes each at most once.

    The caller must first validate any challenge/human-verification result. This
    class enforces ticket lifetime, route allowlisting, minimum dwell time, and
    replay prevention; it does not independently prove humanness or intent quality.
    """

    def __init__(
        self,
        routes: Mapping[str, IntentRoute],
        *,
        max_active_tickets: int = MAX_ACTIVE_TICKETS,
        clock: Callable[[], float] = time.monotonic,
        token_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(routes, Mapping) or not routes:
            raise ValueError("At least one operator-configured intent route is required.")
        checked: dict[str, IntentRoute] = {}
        for intent, route in routes.items():
            if (
                not isinstance(intent, str)
                or not intent.strip()
                or len(intent) > MAX_INTENT_LENGTH
                or not isinstance(route, IntentRoute)
                or not isinstance(route.destination_id, str)
                or not route.destination_id.strip()
                or len(route.destination_id) > MAX_DESTINATION_ID_LENGTH
                or not isinstance(route.content_cid, str)
                or not route.content_cid
                or "/" in route.content_cid
                or " " in route.content_cid
            ):
                raise ValueError("Invalid configured intent route.")
            checked[intent] = route
        if (
            isinstance(max_active_tickets, bool)
            or not isinstance(max_active_tickets, int)
            or not 1 <= max_active_tickets <= MAX_ACTIVE_TICKETS
        ):
            raise ValueError("max_active_tickets is outside the supported range.")
        self._routes = checked
        self._max_active_tickets = max_active_tickets
        self._clock = clock
        self._token_factory = token_factory or (lambda: secrets.token_urlsafe(32))
        self._tickets: dict[bytes, _Ticket] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _digest(handle: str) -> bytes:
        if not isinstance(handle, str) or not 32 <= len(handle) <= 256:
            raise CDDIntentError("Intent ticket is malformed.")
        return hashlib.sha256(handle.encode("ascii", errors="strict")).digest()

    def _prune(self, now: float) -> None:
        for digest, ticket in list(self._tickets.items()):
            if ticket.expires_at <= now or ticket.consumed:
                del self._tickets[digest]

    def issue(
        self,
        intent: str,
        *,
        ttl_seconds: int = 180,
        min_wait_seconds: int = 3,
    ) -> str:
        """Issue an opaque ticket only for a registered intent route."""
        if not isinstance(intent, str) or intent not in self._routes:
            raise CDDIntentError("Intent is not registered for this service.")
        if (
            isinstance(ttl_seconds, bool)
            or not isinstance(ttl_seconds, int)
            or not 1 <= ttl_seconds <= MAX_TICKET_TTL_SECONDS
        ):
            raise CDDIntentError("Ticket TTL is outside the supported range.")
        if (
            isinstance(min_wait_seconds, bool)
            or not isinstance(min_wait_seconds, int)
            or not 0 <= min_wait_seconds <= min(ttl_seconds, MAX_MIN_WAIT_SECONDS)
        ):
            raise CDDIntentError("Minimum wait is outside the supported range.")
        now = self._clock()
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise CDDIntentError("Clock returned an invalid time.")
        handle = self._token_factory()
        digest = self._digest(handle)
        route = self._routes[intent]
        ticket = _Ticket(
            digest=digest,
            intent=intent,
            destination_id=route.destination_id,
            content_cid=route.content_cid,
            issued_at=float(now),
            expires_at=float(now) + ttl_seconds,
            min_wait_seconds=min_wait_seconds,
        )
        with self._lock:
            self._prune(float(now))
            if len(self._tickets) >= self._max_active_tickets:
                raise CDDIntentError("Intent lobby is at capacity; retry later.")
            if digest in self._tickets:
                raise CDDIntentError("Ticket generator collision.")
            self._tickets[digest] = ticket
        return handle

    def consume(self, handle: str) -> IntentGrant:
        """Consume a valid ticket once and return its internal route grant."""
        try:
            digest = self._digest(handle)
        except (CDDIntentError, UnicodeEncodeError) as exc:
            raise CDDIntentError("Intent ticket is malformed.") from exc
        now = self._clock()
        if isinstance(now, bool) or not isinstance(now, (int, float)):
            raise CDDIntentError("Clock returned an invalid time.")
        with self._lock:
            self._prune(float(now))
            ticket = self._tickets.get(digest)
            if ticket is None:
                raise CDDIntentError("Intent ticket is unknown, expired, or already used.")
            if float(now) < ticket.issued_at + ticket.min_wait_seconds:
                raise CDDIntentError("Intent ticket was presented before the minimum wait.")
            if float(now) >= ticket.expires_at:
                del self._tickets[digest]
                raise CDDIntentError("Intent ticket has expired.")
            del self._tickets[digest]
            return IntentGrant(
                intent=ticket.intent,
                destination_id=ticket.destination_id,
                content_cid=ticket.content_cid,
                issued_at=ticket.issued_at,
                expires_at=ticket.expires_at,
            )

    @property
    def active_ticket_count(self) -> int:
        with self._lock:
            self._prune(float(self._clock()))
            return len(self._tickets)
