from app.services.auth import _legacy_hash_password, create_token, decode_token, hash_password, needs_password_upgrade, verify_password
from app.services.controls import RateLimiter
from app.services.voice import capabilities


def test_password_hash_and_token_round_trip() -> None:
    stored = hash_password("secure-password")
    assert stored.startswith("$2")
    assert verify_password("secure-password", stored)
    assert not verify_password("wrong-password", stored)
    legacy = _legacy_hash_password("secure-password")
    assert verify_password("secure-password", legacy)
    assert needs_password_upgrade(legacy)
    assert not needs_password_upgrade(stored)
    assert decode_token(create_token(7, "student"))["sub"] == 7


def test_rate_limiter_rejects_after_limit() -> None:
    limiter = RateLimiter()

    assert limiter.allow("client", limit=1, window=60)
    assert not limiter.allow("client", limit=1, window=60)


def test_voice_capabilities_never_advertise_telephony() -> None:
    assert capabilities()["telephone_calling"]["available"] is False
