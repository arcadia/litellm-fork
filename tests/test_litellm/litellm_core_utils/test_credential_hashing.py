"""
Tests for the shared fail-closed credential-shape gate.

The property under test is that an unrecognised credential shape is hashed rather than
returned in cleartext, WITHOUT changing the output for any shape that was already
recognised - existing sha256 hashes are stable join keys for spend rows, /metrics labels
and audit trails, so re-hashing them would silently break historical attribution.
"""

import hashlib

import pytest

from litellm.constants import (
    LITELLM_INTERNAL_JOBS_SERVICE_ACCOUNT_NAME,
    LITELLM_PROXY_MASTER_KEY_ALIAS,
    LITTELM_CLI_SERVICE_ACCOUNT_NAME,
    LITTELM_INTERNAL_HEALTH_SERVICE_ACCOUNT_NAME,
)
from litellm.litellm_core_utils.credential_hashing import (
    HASHED_JWT_PREFIX,
    hash_credential_fail_closed,
    is_already_hashed_credential,
    is_valid_sha256_hash,
    sanitize_credential_for_logging,
)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# Shapes the old heuristic recognised. Output must be byte-for-byte identical to what
# `hash_token` / the `hashed-jwt-` branch produced before this change.
RECOGNISED_SHAPES = [
    ("sk-1234567890abcdef", _sha256("sk-1234567890abcdef")),
    ("Bearer sk-1234567890abcdef", _sha256("sk-1234567890abcdef")),
    ("bearer sk-1234567890abcdef", _sha256("sk-1234567890abcdef")),
    ("header.payload.signature", f"{HASHED_JWT_PREFIX}{_sha256('header.payload.signature')}"),
    ("Bearer header.payload.signature", f"{HASHED_JWT_PREFIX}{_sha256('header.payload.signature')}"),
]

# Shapes the old heuristic did NOT recognise, and therefore returned in cleartext.
UNRECOGNISED_SHAPES = [
    "some-random-key",
    "opaque-oauth2-access-token",
    "ya29.a0ARrdaM-not-a-jwt",
    "gho_16C7e42F292c6912E7710c838347Ae178B4a",
    "two.parts",
    "a.b.c.d",
]

SENTINELS = [
    LITELLM_PROXY_MASTER_KEY_ALIAS,
    LITTELM_INTERNAL_HEALTH_SERVICE_ACCOUNT_NAME,
    LITTELM_CLI_SERVICE_ACCOUNT_NAME,
    LITELLM_INTERNAL_JOBS_SERVICE_ACCOUNT_NAME,
]


@pytest.mark.parametrize("raw, expected", RECOGNISED_SHAPES)
def test_recognised_shapes_hash_exactly_as_before(raw, expected):
    """No behaviour change for `sk-` keys or JWTs - these values are DB lookup tokens."""
    assert hash_credential_fail_closed(raw) == expected


@pytest.mark.parametrize("raw", UNRECOGNISED_SHAPES)
def test_unrecognised_shapes_are_hashed_not_returned_in_cleartext(raw):
    """The fix: the fallthrough used to `return raw`, leaking the credential to log sinks."""
    result = hash_credential_fail_closed(raw)

    assert result != raw
    assert raw not in result
    assert is_valid_sha256_hash(result)


def test_sk_key_containing_two_dots_still_hashes_bare():
    """
    Order matters. An `sk-` key that happens to contain two dots must hash to a bare
    sha256, not to `hashed-jwt-...`: that value is the key's primary lookup token, so
    testing the JWT shape first would break authentication for such a key.
    """
    key = "sk-abc.def.ghi"

    assert hash_credential_fail_closed(key) == _sha256(key)
    assert not hash_credential_fail_closed(key).startswith(HASHED_JWT_PREFIX)


def test_existing_sha256_passes_through_unchanged():
    """Re-hashing an existing hash would rewrite every historical attribution join key."""
    existing = _sha256("sk-some-key")

    assert hash_credential_fail_closed(existing) == existing


def test_hashed_jwt_marker_passes_through_unchanged():
    """`hashed-jwt-<sha256>` is this module's own output and is not a bare sha256."""
    marker = f"{HASHED_JWT_PREFIX}{_sha256('header.payload.signature')}"

    assert not is_valid_sha256_hash(marker)
    assert is_already_hashed_credential(marker)
    assert hash_credential_fail_closed(marker) == marker


@pytest.mark.parametrize(
    "raw",
    [raw for raw, _ in RECOGNISED_SHAPES] + UNRECOGNISED_SHAPES + SENTINELS + [_sha256("sk-x")],
)
def test_idempotent_for_every_shape(raw):
    """
    `check_api_key` is a `mode="before"` validator, so it re-runs every time a
    `UserAPIKeyAuth` is rebuilt from a dict of already-hashed values, and the logging
    sanitizer re-runs on every logged request. A non-idempotent gate would double-hash.
    """
    once = hash_credential_fail_closed(raw)

    assert hash_credential_fail_closed(once) == once


@pytest.mark.parametrize("sentinel", SENTINELS)
def test_non_credential_sentinels_stay_readable(sentinel):
    """
    These are public constants litellm substitutes INTO `api_key` in place of a
    credential. Hashing them protects nothing and splits each principal's spend rows and
    /metrics labels between a readable alias and an opaque hash.
    """
    assert hash_credential_fail_closed(sentinel) == sentinel


@pytest.mark.parametrize("value", [None, "", 0, 123, {"a": 1}, ["x"]])
def test_non_string_and_empty_values_pass_through(value):
    """Nothing to leak, and the logging sinks cannot assume metadata is well-typed."""
    assert sanitize_credential_for_logging(value) == value


def test_bearer_prefixed_existing_hash_is_not_rehashed():
    existing = _sha256("sk-some-key")

    assert hash_credential_fail_closed(f"Bearer {existing}") == existing


class TestUserAPIKeyAuthIntegration:
    def test_opaque_credential_is_not_stored_in_cleartext(self):
        """
        `proxy/auth/oauth2_check.py` passes the caller's bearer token straight in as
        `api_key`. An opaque (non-`sk-`, non-JWT) token used to be stored verbatim on both
        `api_key` and `token`, and flowed from there into the spend logs.
        """
        from litellm.proxy._types import UserAPIKeyAuth

        opaque = "opaque-oauth2-access-token"
        auth = UserAPIKeyAuth(api_key=opaque)

        assert auth.api_key != opaque
        assert auth.token != opaque
        assert is_valid_sha256_hash(auth.api_key)
        assert is_valid_sha256_hash(auth.token)

    def test_sk_key_hash_is_unchanged(self):
        from litellm.proxy._types import UserAPIKeyAuth

        auth = UserAPIKeyAuth(api_key="sk-1234567890abcdef")

        assert auth.api_key == _sha256("sk-1234567890abcdef")

    def test_jwt_still_hashed_under_marker(self):
        from litellm.proxy._types import UserAPIKeyAuth

        auth = UserAPIKeyAuth(api_key="header.payload.signature")

        assert auth.api_key.startswith(HASHED_JWT_PREFIX)

    def test_service_account_stays_readable(self):
        from litellm.proxy._types import UserAPIKeyAuth

        auth = UserAPIKeyAuth.get_litellm_internal_health_check_user_api_key_auth()

        assert auth.api_key == LITTELM_INTERNAL_HEALTH_SERVICE_ACCOUNT_NAME
        assert auth.key_alias == LITTELM_INTERNAL_HEALTH_SERVICE_ACCOUNT_NAME

    def test_reconstruction_from_hashed_values_is_stable(self):
        from litellm.proxy._types import UserAPIKeyAuth

        auth = UserAPIKeyAuth(api_key="sk-1234567890abcdef")
        rebuilt = UserAPIKeyAuth(**auth.model_dump())

        assert rebuilt.api_key == auth.api_key
        assert rebuilt.token == auth.token


class TestStandardLoggingSanitizer:
    def test_cleartext_user_api_key_hash_is_hashed(self):
        """
        Both `get_standard_logging_metadata` paths blind-copy `user_api_key_hash` out of
        caller-supplied metadata before the `is_valid_sha256_hash` check runs, and that
        check is a conditional overwrite - it cannot unset a cleartext value already
        copied in. The sanitizer is the only gate on the field.
        """
        from litellm.litellm_core_utils.litellm_logging import get_standard_logging_metadata

        clean = get_standard_logging_metadata(metadata={"user_api_key_hash": "opaque-oauth2-access-token"})

        assert clean["user_api_key_hash"] != "opaque-oauth2-access-token"
        assert is_valid_sha256_hash(clean["user_api_key_hash"])

    def test_existing_hash_survives_the_sanitizer(self):
        from litellm.litellm_core_utils.litellm_logging import get_standard_logging_metadata

        existing = _sha256("sk-some-key")
        clean = get_standard_logging_metadata(metadata={"user_api_key_hash": existing})

        assert clean["user_api_key_hash"] == existing
