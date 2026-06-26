from app.core.config import Settings
from app.services.anonymous_actor import resolve_anonymous_actor


def test_anonymous_actor_tokens_are_signed_and_stable() -> None:
    settings = Settings(anonymous_actor_secret="test-secret")

    first = resolve_anonymous_actor(None, settings)
    repeated = resolve_anonymous_actor(first.token, settings)
    tampered = resolve_anonymous_actor(f"{first.token}tampered", settings)

    assert first.is_new is True
    assert repeated.is_new is False
    assert repeated.actor_hash == first.actor_hash
    assert tampered.is_new is True
    assert tampered.actor_hash != first.actor_hash
