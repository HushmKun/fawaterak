from __future__ import annotations

import dataclasses

import pytest

from fawaterak._http import DEFAULT_TIMEOUT_SECONDS
from fawaterak.config import (
	ENV_CLIENT_ID,
	ENV_CLIENT_SECRET,
	ENV_ENVIRONMENT,
	ENV_VENDOR_API_KEY,
	Config,
	SingletonMeta,
)
from fawaterak.exceptions import FawaterakConfigException

# --------------------------------------------------------------------------
# Happy path: everything passed explicitly
# --------------------------------------------------------------------------


class TestResolveExplicitArgs:
	def test_explicit_staging(self) -> None:
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert config.client_id == "cid"
		assert config.client_secret == "secret"
		assert config.environment == "staging"
		assert config.base_url == "https://staging.fawaterk.com"

	def test_explicit_production(self) -> None:
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="production"
		)
		assert config.environment == "production"
		assert config.base_url == "https://app.fawaterk.com"

	def test_base_url_override_ignores_default_urls(self) -> None:
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			base_url="https://mock.local:8080",
		)
		assert config.base_url == "https://mock.local:8080"

	def test_base_url_trailing_slash_is_stripped(self) -> None:
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			base_url="https://mock.local:8080/",
		)
		assert config.base_url == "https://mock.local:8080"

	def test_vendor_api_key_passed_through(self) -> None:
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			environment="staging",
			vendor_api_key="vendor-key-123",
		)
		assert config.vendor_api_key == "vendor-key-123"

	def test_vendor_api_key_defaults_to_none(self) -> None:
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert config.vendor_api_key is None


# --------------------------------------------------------------------------
# Environment-variable fallback
# --------------------------------------------------------------------------


class TestResolveEnvFallback:
	def test_client_id_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
		monkeypatch.setenv(ENV_CLIENT_ID, "env-cid")
		config = Config.resolve(client_secret="secret", environment="staging")
		assert config.client_id == "env-cid"

	def test_client_secret_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
		monkeypatch.setenv(ENV_CLIENT_SECRET, "env-secret")
		config = Config.resolve(client_id="cid", environment="staging")
		assert config.client_secret == "env-secret"

	def test_environment_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
		monkeypatch.setenv(ENV_ENVIRONMENT, "production")
		config = Config.resolve(client_id="cid", client_secret="secret")
		assert config.environment == "production"
		assert config.base_url == "https://app.fawaterk.com"

	def test_vendor_api_key_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
		monkeypatch.setenv(ENV_VENDOR_API_KEY, "env-vendor-key")
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert config.vendor_api_key == "env-vendor-key"

	def test_all_values_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
		monkeypatch.setenv(ENV_CLIENT_ID, "env-cid")
		monkeypatch.setenv(ENV_CLIENT_SECRET, "env-secret")
		monkeypatch.setenv(ENV_ENVIRONMENT, "staging")
		monkeypatch.setenv(ENV_VENDOR_API_KEY, "env-vendor-key")

		config = Config.resolve()

		assert config.client_id == "env-cid"
		assert config.client_secret == "env-secret"
		assert config.environment == "staging"
		assert config.vendor_api_key == "env-vendor-key"
		assert config.base_url == "https://staging.fawaterk.com"


# --------------------------------------------------------------------------
# Precedence: explicit argument beats env var
# --------------------------------------------------------------------------


class TestResolvePrecedence:
	def test_explicit_client_id_beats_env(
		self, monkeypatch: pytest.MonkeyPatch
	) -> None:
		monkeypatch.setenv(ENV_CLIENT_ID, "env-cid")
		config = Config.resolve(
			client_id="explicit-cid", client_secret="secret", environment="staging"
		)
		assert config.client_id == "explicit-cid"

	def test_explicit_environment_beats_env(
		self, monkeypatch: pytest.MonkeyPatch
	) -> None:
		monkeypatch.setenv(ENV_ENVIRONMENT, "production")
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert config.environment == "staging"
		assert config.base_url == "https://staging.fawaterk.com"

	def test_base_url_beats_env_environment(
		self, monkeypatch: pytest.MonkeyPatch
	) -> None:
		monkeypatch.setenv(ENV_ENVIRONMENT, "staging")
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			base_url="https://mock.local",
		)
		assert config.base_url == "https://mock.local"

	def test_explicit_empty_string_falls_back_to_env(
		self, monkeypatch: pytest.MonkeyPatch
	) -> None:
		"""Documents current behavior: '' is falsy, so `x or env` skips it.

		Passing client_id="" is treated the same as not passing it at all.
		"""
		monkeypatch.setenv(ENV_CLIENT_ID, "env-cid")
		config = Config.resolve(
			client_id="", client_secret="secret", environment="staging"
		)
		assert config.client_id == "env-cid"


# --------------------------------------------------------------------------
# Missing required credentials
# --------------------------------------------------------------------------


class TestResolveMissingCredentials:
	def test_missing_client_id_raises(self) -> None:
		with pytest.raises(FawaterakConfigException, match="client_id"):
			Config.resolve(client_secret="secret", environment="staging")

	def test_missing_client_secret_raises(self) -> None:
		with pytest.raises(FawaterakConfigException, match="client_secret"):
			Config.resolve(client_id="cid", environment="staging")

	def test_missing_both_reports_both_in_one_error(self) -> None:
		with pytest.raises(FawaterakConfigException) as exc_info:
			Config.resolve(environment="staging")
		message = str(exc_info.value)
		assert "client_id" in message
		assert "client_secret" in message

	def test_credential_error_mentions_env_var_names(self) -> None:
		with pytest.raises(FawaterakConfigException) as exc_info:
			Config.resolve(environment="staging")
		message = str(exc_info.value)
		assert ENV_CLIENT_ID in message
		assert ENV_CLIENT_SECRET in message

	def test_missing_credentials_checked_before_missing_environment(self) -> None:
		"""Credential validation happens first, so a config missing both

		credentials AND environment/base_url should fail on credentials,
		not on the environment check.
		"""
		with pytest.raises(FawaterakConfigException, match="client_id"):
			Config.resolve()


# --------------------------------------------------------------------------
# Environment / base_url resolution edge cases
# --------------------------------------------------------------------------


class TestResolveEnvironmentEdgeCases:
	def test_no_environment_and_no_base_url_raises(self) -> None:
		with pytest.raises(FawaterakConfigException, match="environment"):
			Config.resolve(client_id="cid", client_secret="secret")

	def test_invalid_environment_string_without_base_url_raises(self) -> None:
		with pytest.raises(FawaterakConfigException, match="environment"):
			Config.resolve(client_id="cid", client_secret="secret", environment="prod")

	def test_invalid_environment_error_includes_offending_value(self) -> None:
		with pytest.raises(FawaterakConfigException, match="not-a-real-env"):
			Config.resolve(
				client_id="cid",
				client_secret="secret",
				environment="not-a-real-env",
			)

	def test_invalid_environment_but_base_url_given_does_not_raise(self) -> None:
		"""An unrecognized `environment` is fine as long as base_url covers it."""
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			environment="not-a-real-env",
			base_url="https://mock.local",
		)
		assert config.base_url == "https://mock.local"
		assert config.environment is None

	def test_environment_field_still_set_when_base_url_also_given(self) -> None:
		"""Current behavior: passing a *valid* environment alongside base_url

		still populates `config.environment`, even though `base_url` is what
		determines `config.base_url`. The class docstring says `environment`
		is None "if base_url was supplied instead", but in practice it's
		only None when no *valid* environment string was resolvable at all.
		"""
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			environment="staging",
			base_url="https://mock.local",
		)
		assert config.environment == "staging"
		assert config.base_url == "https://mock.local"


# --------------------------------------------------------------------------
# Timeout
# --------------------------------------------------------------------------


class TestResolveTimeout:
	def test_default_timeout_used_when_not_specified(self) -> None:
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert config.timeout == DEFAULT_TIMEOUT_SECONDS

	def test_explicit_timeout_override(self) -> None:
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			environment="staging",
			timeout=5.0,
		)
		assert config.timeout == 5.0


# --------------------------------------------------------------------------
# Dataclass behavior: immutability and secret redaction
# --------------------------------------------------------------------------


class TestConfigDataclassBehavior:
	def test_config_is_frozen(self) -> None:
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		with pytest.raises(dataclasses.FrozenInstanceError):
			config.client_id = "someone-else"  # ty: ignore[invalid-assignment]

	def test_repr_excludes_client_secret(self) -> None:
		config = Config.resolve(
			client_id="cid",
			client_secret="super-secret-value",
			environment="staging",
		)
		assert "super-secret-value" not in repr(config)

	def test_repr_excludes_vendor_api_key(self) -> None:
		config = Config.resolve(
			client_id="cid",
			client_secret="secret",
			environment="staging",
			vendor_api_key="super-secret-vendor-key",
		)
		assert "super-secret-vendor-key" not in repr(config)

	def test_repr_includes_non_secret_fields(self) -> None:
		config = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert "cid" in repr(config)
		assert "staging" in repr(config)

	def test_direct_construction_still_works(self) -> None:
		"""Config itself has no validation; that lives in `resolve()`.

		Constructing directly is documented as discouraged but not blocked.
		"""
		config = Config(
			client_id="cid",
			client_secret="secret",
			base_url="https://mock.local",
		)
		assert config.client_id == "cid"
		assert config.environment is None
		assert config.timeout == DEFAULT_TIMEOUT_SECONDS


# --------------------------------------------------------------------------
# Singleton behavior (SingletonMeta)
#
# Config is a process-wide singleton: the *first* successful construction —
# whether via Config(...) directly or Config.resolve(...) — wins, and every
# later call returns that same instance regardless of what arguments it's
# given. These tests pin that contract down explicitly, since it's easy to
# accidentally change (e.g. by keying the cache on args, or removing the
# metaclass) without anything else in the suite catching it — the tests
# above only ever build one Config per test, so they can't see this.
# --------------------------------------------------------------------------


class TestSingletonBehavior:
	def test_repeated_resolve_returns_the_same_instance(self) -> None:
		first = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		second = Config.resolve(
			client_id="cid", client_secret="secret", environment="staging"
		)
		assert first is second

	def test_second_resolve_call_ignores_new_arguments(self) -> None:
		"""Once built, later resolve() calls with *different* args still

		return the original instance — the new args are silently discarded.
		Intentional given the singleton design, but surprising enough to be
		worth pinning down explicitly.
		"""
		first = Config.resolve(
			client_id="first-cid", client_secret="first-secret", environment="staging"
		)
		second = Config.resolve(
			client_id="second-cid",
			client_secret="second-secret",
			environment="production",
		)

		assert second is first
		assert second.client_id == "first-cid"
		assert second.environment == "staging"

	def test_direct_construction_and_resolve_share_one_instance(self) -> None:
		direct = Config(
			client_id="direct-cid",
			client_secret="direct-secret",
			base_url="https://mock.local",
		)
		via_resolve = Config.resolve(
			client_id="resolve-cid",
			client_secret="resolve-secret",
			environment="production",
		)

		assert via_resolve is direct
		assert via_resolve.client_id == "direct-cid"

	def test_singleton_ignores_env_vars_changed_after_first_build(
		self, monkeypatch: pytest.MonkeyPatch
	) -> None:
		monkeypatch.setenv(ENV_CLIENT_ID, "env-cid-v1")
		first = Config.resolve(client_secret="secret", environment="staging")

		monkeypatch.setenv(ENV_CLIENT_ID, "env-cid-v2")
		second = Config.resolve(client_secret="secret", environment="staging")

		assert second is first
		assert second.client_id == "env-cid-v1"

	def test_clearing_the_cache_allows_a_fresh_instance(self) -> None:
		"""Documents the reset mechanism itself (what this file's autouse

		fixture relies on), so a refactor of SingletonMeta gets caught here
		rather than surfacing as confusing failures elsewhere.
		"""
		first = Config.resolve(
			client_id="first-cid", client_secret="secret", environment="staging"
		)

		SingletonMeta._instances.clear()

		second = Config.resolve(
			client_id="second-cid", client_secret="secret", environment="production"
		)

		assert second is not first
		assert second.client_id == "second-cid"
		assert second.environment == "production"

	def test_only_one_instance_is_ever_cached(self) -> None:
		Config.resolve(client_id="cid", client_secret="secret", environment="staging")
		assert len(SingletonMeta._instances) == 1
		assert Config in SingletonMeta._instances
