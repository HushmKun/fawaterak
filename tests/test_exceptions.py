"""Unit tests for the Fawaterak SDK exception hierarchy."""

from __future__ import annotations

import pytest

from fawaterak.exceptions import (
	FawaterakAPIException,
	FawaterakAuthException,
	FawaterakConfigException,
	FawaterakConnectionException,
	FawaterakException,
	FawaterakTemporaryException,
	FawaterakValidationException,
	FawaterakWebhookException,
)

SDK_ERRORS = [
	FawaterakException("base"),
	FawaterakConfigException("missing client_id"),
	FawaterakConnectionException("connection reset"),
	FawaterakWebhookException("bad signature"),
	FawaterakAPIException("server error", 500),
	FawaterakAuthException("bad credentials", 401),
	FawaterakValidationException("bad field", 422),
	FawaterakTemporaryException("try later", 503),
]


@pytest.mark.parametrize("error", SDK_ERRORS, ids=lambda error: type(error).__name__)
def test_except_exception_catches_sdk_errors(error: FawaterakException) -> None:
	"""Framework error handlers, retry helpers and task runners catch
	`Exception`; SDK errors must not slip past them the way SystemExit does."""
	caught: Exception | None = None
	try:
		raise error
	except Exception as exc:  # noqa: BLE001 — the blind catch is what's under test
		caught = exc
	assert caught is error
