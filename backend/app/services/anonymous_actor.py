import hashlib
import hmac
from dataclasses import dataclass
from uuid import uuid4

from app.core.config import Settings

ACTOR_COOKIE_NAME = "civicpulse_actor"
ACTOR_COOKIE_MAX_AGE = 60 * 60 * 24 * 365


@dataclass(frozen=True, slots=True)
class AnonymousActor:
    actor_hash: str
    token: str
    is_new: bool


def _signature(actor_id: str, secret: str) -> str:
    return hmac.new(secret.encode(), actor_id.encode(), hashlib.sha256).hexdigest()


def resolve_anonymous_actor(token: str | None, settings: Settings) -> AnonymousActor:
    actor_id: str | None = None
    if token:
        candidate_id, separator, candidate_signature = token.partition(".")
        if separator and hmac.compare_digest(
            candidate_signature,
            _signature(candidate_id, settings.anonymous_actor_secret),
        ):
            actor_id = candidate_id

    is_new = actor_id is None
    actor_id = actor_id or uuid4().hex
    signed_token = f"{actor_id}.{_signature(actor_id, settings.anonymous_actor_secret)}"
    actor_hash = hashlib.sha256(actor_id.encode()).hexdigest()
    return AnonymousActor(actor_hash=actor_hash, token=signed_token, is_new=is_new)
