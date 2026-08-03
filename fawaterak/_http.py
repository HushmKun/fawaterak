"""HTTP session wrapper and the single choke point every SDK method routes through.

All error mapping (network failures, auth retry, validation, transient errors)
lives in one place here so it isn't duplicated across every public client
method (get_payment_methods, create_transaction, get_refund, ...).
"""

from __future__ import annotations

import sys
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

if sys.version_info >= (3, 11):
	from typing import Self
else:
	from typing_extensions import Self

JSONDict = dict[str, Any]

from .auth import TokenManager
from .exceptions import (
	FawaterakAPIException,
	FawaterakAuthException,
	FawaterakConnectionException,
	FawaterakTemporaryException,
	FawaterakValidationException,
)

DEFAULT_TIMEOUT_SECONDS = 30.0

# Transport-level retries only cover connection-level hiccups and 503s on
# safe, idempotent methods (GET). Most calls are POST, which is deliberately
# excluded here.
_TRANSPORT_RETRY = Retry(
	total=3,
	backoff_factor=0.5,
	status_forcelist=(503,),
	allowed_methods=frozenset({"GET"}),
	raise_on_status=False,
)


class HTTPClient:
	"""Owns the requests.Session, auth headers, and error-mapping logic.

	Every public SDK method should call `.request()` on an instance of this
	class rather than touching `requests` directly.
	"""

	def __init__(
		self,
		base_url: str,
		token_manager: TokenManager,
		timeout: float = DEFAULT_TIMEOUT_SECONDS,
	) -> None:
		self._base_url = base_url.rstrip("/")
		self._token_manager = token_manager
		self._timeout = timeout
		self._session = self._build_session()

	@staticmethod
	def _build_session() -> requests.Session:
		session = requests.Session()
		adapter = HTTPAdapter(max_retries=_TRANSPORT_RETRY)
		session.mount("https://", adapter)
		session.mount("http://", adapter)
		return session

	def request(
		self,
		method: str,
		path: str,
		*,
		json: JSONDict | None = None,
		params: JSONDict | None = None,
		_retried: bool = False,
	) -> JSONDict:
		"""Make one API call and return its decoded JSON body.

		Maps failures as follows:
		  - no response received                -> FawaterakConnectionError
		  - 401, first occurrence                -> refresh token, retry once
		  - 401, after that retry also fails     -> FawaterakAuthError
		  - 400 / 422                            -> FawaterakValidationError
		  - 503                                  -> FawaterakTemporaryError
		  - any other non-2xx                    -> FawaterakAPIError
		"""
		url = f"{self._base_url}{path}"
		headers = {
			"Authorization": f"Bearer {self._token_manager.access_token}",
			"Accept": "application/json",
			"Content-Type": "application/json",
		}

		try:
			response = self._session.request(
				method,
				url,
				json=json,
				params=params,
				headers=headers,
				timeout=self._timeout,
			)
		except requests.exceptions.RequestException as exc:
			raise FawaterakConnectionException(str(exc)) from exc

		if response.status_code == 401 and not _retried:
			self._token_manager.refresh()
			return self.request(method, path, json=json, params=params, _retried=True)

		if response.ok:
			return self._decode_or_raise(response)

		body = self._decode(response)
		message = body.get("message", response.text) if body else response.text

		if response.status_code in (400, 422):
			raise FawaterakValidationException(message, response.status_code, body)
		if response.status_code == 401:
			raise FawaterakAuthException(message, response.status_code, body)
		if response.status_code == 503:
			raise FawaterakTemporaryException(message, response.status_code, body)
		raise FawaterakAPIException(message, response.status_code, body)

	def _decode_or_raise(self, response: requests.Response) -> JSONDict:
		"""Decode a successful (2xx) response, raising if the body isn't JSON."""
		try:
			data: JSONDict = response.json()
		except ValueError:
			raise FawaterakAPIException(
				f"Fawaterak returned a non-JSON 2xx response (status {response.status_code})",
				response.status_code,
				{"raw_text": response.text},
			) from None
		return data

	@staticmethod
	def _decode(response: requests.Response) -> JSONDict:
		"""Best-effort decode of an error response body; never raises."""
		try:
			data: JSONDict = response.json()
		except ValueError:
			return {}
		return data

	def close(self) -> None:
		self._session.close()

	def __enter__(self) -> Self:
		return self

	def __exit__(self, *exc_info: object) -> None:
		self.close()
