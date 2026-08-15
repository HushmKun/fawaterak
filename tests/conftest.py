from __future__ import annotations

import pytest

from fawaterak.config import (
	ENV_CLIENT_ID,
	ENV_CLIENT_SECRET,
	ENV_ENVIRONMENT,
	ENV_VENDOR_API_KEY,
	SingletonMeta,
)

_ALL_CONFIG_ENV_VARS = (
	ENV_CLIENT_ID,
	ENV_CLIENT_SECRET,
	ENV_VENDOR_API_KEY,
	ENV_ENVIRONMENT,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
	"""Ensure no Fawaterak env var leaks in from the host shell.

	Without this, a developer with FAWATERAK_CLIENT_ID exported locally
	(or a CI secret) would get tests that pass for the wrong reason.
	"""
	for var in _ALL_CONFIG_ENV_VARS:
		monkeypatch.delenv(var, raising=False)


@pytest.fixture(autouse=True)
def reset_singleton() -> None:  # ty: ignore[invalid-return-type]
	"""Config is a singleton: the first construction in the process wins,
	and every later call — with whatever args — returns that same cached
	instance. Without resetting this between tests, test order would
	determine results (whichever test runs first "poisons" the rest).

	This mirrors what a real process would need too, e.g. a test harness
	or a long-running worker that wants to rebuild config on reload.
	"""
	SingletonMeta._instances.clear()
	yield
	SingletonMeta._instances.clear()
