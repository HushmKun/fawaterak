"""OAuth2 client-credentials token management for the Fawaterak SDK.

TokenManager owns the exchange (POST /oauth/token, grant_type=client_credentials)
and refresh (grant_type=refresh_token) flows, caches the access token with its
expiry, and transparently renews it. Nothing else in the SDK should talk to
/oauth/token directly.
"""

from __future__ import annotations

import threading
import time
from importlib.metadata import version
from platform import python_version, release, system
from typing import Any

import requests

from .exceptions import FawaterakAuthException, FawaterakConnectionException

# Refresh this many seconds before the token's actual expiry, so a request
# started right before expiry doesn't race the clock.
_SAFETY_MARGIN_SECONDS = 30


class TokenManager:
	def __init__(
		self,
		client_id: str,
		client_secret: str,
		base_url: str,
		session: requests.Session | None = None,
	) -> None:
		self._client_id = client_id
		self._client_secret = client_secret
		self._base_url = base_url.rstrip("/")
		self._session = session or self._build_session()
		self._lock = threading.Lock()

		self._access_token: str | None = None
		self._refresh_token: str | None = None
		self._expires_at: float = 0.0

	@staticmethod
	def _build_session() -> requests.Session:
		session = requests.Session()
		session.headers["User-Agent"] = (
			f"Fawaterak-sdk-auth/{version('fawaterak')} Python/{python_version()} {system()}/{release()}"
		)
		return session

	@property
	def access_token(self) -> str | None:
		"""Current valid access token, refreshing first if it's missing or stale.

		Safe to call from multiple threads: the check-and-refresh is atomic,
		so concurrent callers block briefly on one refresh rather than each
		firing their own /oauth/token request.
		"""
		with self._lock:
			if self._access_token is None or time.time() >= self._expires_at:
				self._refresh_or_exchange()
			return self._access_token

	def refresh(self, force: bool = False) -> None:
		"""Force a refresh regardless of cached expiry.

		Called by HTTPClient.request() after a 401 — the cached token may
		look unexpired but the server has already invalidated it.
		"""
		with self._lock:
			if time.time() >= self._expires_at or force:
				self._refresh_or_exchange()

	def _refresh_or_exchange(self) -> None:
		if self._refresh_token:
			payload = {
				"grant_type": "refresh_token",
				"refresh_token": self._refresh_token,
				"client_id": self._client_id,
				"client_secret": self._client_secret,
			}
		else:
			payload = {
				"grant_type": "client_credentials",
				"client_id": self._client_id,
				"client_secret": self._client_secret,
			}

		try:
			response = self._session.post(f"{self._base_url}/oauth/token", json=payload)
		except requests.exceptions.RequestException as exc:
			raise FawaterakConnectionException(str(exc)) from exc

		if not response.ok:
			if self._refresh_token:
				self._refresh_token = None
				self._refresh_or_exchange()
				return
			body = self._safe_json(response)
			raise FawaterakAuthException(
				body.get("message", "OAuth token exchange failed"),
				response.status_code,
				body,
			)

		data = self._safe_json(response)
		self._access_token = data["access_token"]
		self._refresh_token = data.get("refresh_token", self._refresh_token)
		self._expires_at = time.time() + data["expires_in"] - _SAFETY_MARGIN_SECONDS

	@staticmethod
	def _safe_json(response: requests.Response) -> dict[str, Any]:
		try:
			data: dict[str, Any] = response.json()
		except ValueError:
			return {}
		return data
