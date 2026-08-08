"""
The single credential-shape gate shared by the auth hasher, the spend-log writer and the
standard-logging metadata sink.

`UserAPIKeyAuth._safe_hash_litellm_api_key` (`litellm/proxy/_types.py`) and
`_hash_api_key_for_spend_log` (`litellm/proxy/spend_tracking/spend_tracking_utils.py`)
each carried their own copy of the same heuristic: strip a `Bearer ` prefix, hash an
`sk-` key, and return anything else unchanged. Two copies of one control are not defence
in depth - a credential outside `{sk-*, dotted JWT}` defeated both at once and was
persisted verbatim: into the SpendLogs `api_key` column, and - via `user_api_key_hash` -
into whatever the standard-logging sink writes to (S3, GCS, a webhook, ...).

The heuristic lives here once, and its fallthrough fails closed: an unrecognised shape is
hashed rather than returned. This is the policy `redact_credential_headers` already
applies to credential *headers*; this applies it to the key field.

Deliberately stdlib-only (plus `litellm.constants`, which is a leaf module):
`litellm_core_utils.litellm_logging` imports this on the SDK path, which must not pull in
`litellm.proxy`.
"""

import hashlib
import re
from typing import Final

from litellm.constants import (
    LITELLM_INTERNAL_JOBS_SERVICE_ACCOUNT_NAME,
    LITELLM_PROXY_MASTER_KEY_ALIAS,
    LITTELM_CLI_SERVICE_ACCOUNT_NAME,
    LITTELM_INTERNAL_HEALTH_SERVICE_ACCOUNT_NAME,
)

# A sanitized JWT keeps a marker so downstream attribution can still tell a JWT principal
# apart from a virtual key. This is the shape `_safe_hash_litellm_api_key` already emits.
HASHED_JWT_PREFIX: Final = "hashed-jwt-"

_SHA256_HEX: Final = re.compile(r"[a-fA-F0-9]{64}")

_BEARER_PREFIX_LENGTH: Final = len("bearer ")

# litellm's own non-credential principals. These are public constants that litellm
# substitutes INTO `api_key` *in place of* a real credential - the master-key alias exists
# precisely so the master key never propagates downstream - and their readability is the
# whole point: they label spend rows, Prometheus /metrics labels and audit trails. Hashing
# them would protect nothing (they are public, and there is no secret behind them) while
# splitting each principal's attribution between a readable alias and an opaque hash.
#
# This is not an allowlist for credentials: no value here is one, and no caller-supplied
# key can collide with one. That second half is enforced in
# `proxy/management_endpoints/key_management_endpoints.py`, where
# `_common_key_generation_helper` rejects any caller-supplied key that does not start with
# `sk-`. That invariant matters beyond attribution: membership is also read as
# authorization, e.g. `can_modify_verification_token` compares `api_key` directly against
# `LITELLM_INTERNAL_JOBS_SERVICE_ACCOUNT_NAME`. Do not add a value here that a caller
# could ever supply.
_NON_CREDENTIAL_SENTINELS: Final = frozenset(
    {
        LITELLM_PROXY_MASTER_KEY_ALIAS,
        LITTELM_INTERNAL_HEALTH_SERVICE_ACCOUNT_NAME,
        LITTELM_CLI_SERVICE_ACCOUNT_NAME,
        LITELLM_INTERNAL_JOBS_SERVICE_ACCOUNT_NAME,
    }
)


def is_valid_sha256_hash(value: str) -> bool:
    """Check if the value is a valid SHA-256 hash (64 hexadecimal characters)."""
    return bool(_SHA256_HEX.fullmatch(value))


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def is_already_hashed_credential(value: str) -> bool:
    """
    True for the two output shapes this module produces.

    Both are stable join keys for downstream spend/attribution analytics, so they must
    survive re-normalisation byte for byte. `UserAPIKeyAuth.check_api_key` is a
    `mode="before"` validator that re-runs every time a `UserAPIKeyAuth` is rebuilt from a
    dict of already-hashed values, and the logging sanitizer re-runs on every logged
    request, so a normaliser that re-hashed its own output would silently rewrite every
    historical join key.
    """
    if is_valid_sha256_hash(value):
        return True
    if value.startswith(HASHED_JWT_PREFIX):
        return is_valid_sha256_hash(value[len(HASHED_JWT_PREFIX) :])
    return False


def hash_credential_fail_closed(credential: str) -> str:
    """
    Return a value that is safe to persist, whatever shape the credential has.

    Idempotent: `f(f(x)) == f(x)` for every input.

    - already-hashed values (64-hex, or `hashed-jwt-<64-hex>`) pass through untouched
    - empty values pass through untouched (nothing to leak)
    - litellm's own non-credential sentinels pass through, see `_NON_CREDENTIAL_SENTINELS`
    - an `sk-` key is hashed to a bare sha256, exactly as `hash_token` did
    - a 3-part JWT is hashed under the `hashed-jwt-` marker, as before
    - **everything else** is hashed too. That fallthrough is the fix: it used to return
      the credential unchanged, so any shape the heuristic did not recognise - an opaque
      OAuth2 bearer token, for instance - was persisted in cleartext.

    Note: a raw secret that happens to be exactly 64 hex characters is indistinguishable
    from an already-computed hash and passes through. That is a deliberate and unavoidable
    consequence of keeping existing hashes stable.
    """
    if not credential:
        return credential
    if is_already_hashed_credential(credential):
        return credential
    if credential in _NON_CREDENTIAL_SENTINELS:
        return credential

    normalized = credential
    if normalized[:_BEARER_PREFIX_LENGTH].lower() == "bearer ":
        normalized = normalized[_BEARER_PREFIX_LENGTH:]
    # "Bearer <already-hashed>" is still already hashed.
    if is_already_hashed_credential(normalized):
        return normalized
    if not normalized:
        return credential

    # Order matters, and matches the behaviour this replaces: an `sk-` key that happens to
    # contain two dots must still hash to a bare sha256, because that value is the key's
    # primary lookup token. Testing the JWT shape first would rewrite it.
    if normalized.startswith("sk-"):
        return _sha256(normalized)
    if len(normalized.split(".")) == 3:
        return f"{HASHED_JWT_PREFIX}{_sha256(normalized)}"
    return _sha256(normalized)


def sanitize_credential_for_logging(value: str | None) -> str | None:
    """
    Tolerant wrapper over `hash_credential_fail_closed` for the logging sinks, which read
    `user_api_key_hash` straight out of caller-supplied metadata. Empty values pass
    through untouched - there is nothing to leak - and the `isinstance` guard keeps a
    mistyped value from raising on a logging path, since that metadata reaches us from
    arbitrary callers rather than from a validated model.
    """
    if not value or not isinstance(value, str):
        return value
    return hash_credential_fail_closed(value)
