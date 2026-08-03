"""Configuration resolution for the Fawaterak SDK: credentials, environment, base URL.

Resolution is intentionally explicit rather than magic: values passed
directly to `Config.resolve()` always win, environment variables are the
fallback, and there is no default environment. Silently defaulting to
"production" (or to "staging") is exactly the kind of mistake a payment SDK
shouldn't paper over — if the caller hasn't said which one they mean, that's
a configuration error, not a guess for the SDK to make.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Literal

from ._http import DEFAULT_TIMEOUT_SECONDS
from .exceptions import FawaterakConfigException

Environment = Literal["staging", "production"]

_BASE_URLS: dict[Environment, str] = {
	"staging": "https://staging.fawaterk.com",
	"production": "https://app.fawaterk.com",
}

ENV_CLIENT_ID = "FAWATERAK_CLIENT_ID"
ENV_CLIENT_SECRET = "FAWATERAK_CLIENT_SECRET"
ENV_VENDOR_API_KEY = "FAWATERAK_VENDOR_API_KEY"
ENV_ENVIRONMENT = "FAWATERAK_ENV"


def _parse_environment(value: str | None) -> Environment | None:
	"""Explicit literal comparison (not a dict membership check) so mypy can
	actually narrow the return type to `Environment | None` in strict mode.
	"""
	if value == "staging":
		return "staging"
	if value == "production":
		return "production"
	return None


class SingletonMeta(type):
	"""
	A metaclass for creating singletons,
	lacks thread-safety due to lack of necessity.
	"""

	_instances: ClassVar[Dict[Any, Any]] = {}

	def __call__(cls, *args: Any, **kwargs: Any) -> Any:
		if cls not in cls._instances:
			instance = super().__call__(*args, **kwargs)
			cls._instances[cls] = instance
		return cls._instances[cls]


@dataclass(frozen=True)
class Config(metaclass=SingletonMeta):
	"""Resolved configuration used to construct TokenManager/HTTPClient.

	Construct this via `Config.resolve(...)` rather than directly for first-time
	— that's where env var fallback and validation happen, subsequent usage can use
	`Config()` directly since it returns the singelton object.

	Attributes:
	    client_id: OAuth client id, used for the /api/v3/* endpoints.
	    client_secret: OAuth client secret. Excluded from repr()/logs.
	    base_url: Resolved from `environment`, or a direct override (e.g. to
	        point at a local mock server in tests).
	    environment: "staging" or "production" if a recognized one was given;
	        `None` if `base_url` was supplied directly instead.
	    vendor_api_key: Legacy static key, only needed for the Phase 8
	        tokenization endpoints and for webhook signature verification.
	        Optional because most of the SDK's v3 surface never uses it.
	        Excluded from repr()/logs.
	    timeout: Default per-request timeout, in seconds.
	"""

	client_id: str
	client_secret: str = field(repr=False)
	base_url: str
	environment: Environment | None = None
	vendor_api_key: str | None = field(default=None, repr=False)
	timeout: float = DEFAULT_TIMEOUT_SECONDS

	@classmethod
	def resolve(
		cls,
		*,
		client_id: str | None = None,
		client_secret: str | None = None,
		environment: str | None = None,
		base_url: str | None = None,
		vendor_api_key: str | None = None,
		timeout: float = DEFAULT_TIMEOUT_SECONDS,
	) -> Config:
		"""
		Build a Config from explicit args, falling back to env vars.

		    Precedence:
		        - explicit argument
		        - matching env var.

		    Args:
		        - client_id: OAuth client id. Falls back to $FAWATERAK_CLIENT_ID.
		        - client_secret: OAuth client secret. Falls back to
		            $FAWATERAK_CLIENT_SECRET.
		        - environment: "staging" or "production". Falls back to
		            $FAWATERAK_ENV. Ignored if `base_url` is also given.
		        - base_url: Explicit API base URL, overriding `environment`
		            entirely. Mainly for pointing at a local mock server in tests.
		        - vendor_api_key: Legacy vendor key, needed only for Phase 8
		            (tokenization) and webhook verification. Falls back to
		            $FAWATERAK_VENDOR_API_KEY.
		        - timeout: Default per-request timeout, in seconds.

		    Raises:
		    FawaterakConfigError: if client_id/client_secret are missing after
		        checking both the argument and env var, or if no valid
		        `environment` was resolved and no `base_url` override was
		        given either.
		"""
		resolved_client_id = client_id or os.environ.get(ENV_CLIENT_ID)
		resolved_client_secret = client_secret or os.environ.get(ENV_CLIENT_SECRET)
		resolved_vendor_key = vendor_api_key or os.environ.get(ENV_VENDOR_API_KEY)
		resolved_environment = _parse_environment(
			environment or os.environ.get(ENV_ENVIRONMENT)
		)

		missing = []
		if not resolved_client_id:
			missing.append(f"client_id (or ${ENV_CLIENT_ID})")
		if not resolved_client_secret:
			missing.append(f"client_secret (or ${ENV_CLIENT_SECRET})")
		if missing:
			raise FawaterakConfigException(
				"Missing required Fawaterak configuration: " + ", ".join(missing)
			)

		if base_url is not None:
			resolved_base_url = base_url.rstrip("/")
		elif resolved_environment is not None:
			resolved_base_url = _BASE_URLS[resolved_environment]
		else:
			raise FawaterakConfigException(
				"environment must be 'staging' or 'production' "
				f"(directly, or via ${ENV_ENVIRONMENT}); got "
				f"{environment or os.environ.get(ENV_ENVIRONMENT)!r}. "
				"Alternatively, pass base_url directly (For testing purposes)."
			)

		assert resolved_client_id is not None
		assert resolved_client_secret is not None

		return cls(
			client_id=resolved_client_id,
			client_secret=resolved_client_secret,
			base_url=resolved_base_url,
			environment=resolved_environment,
			vendor_api_key=resolved_vendor_key,
			timeout=timeout,
		)
