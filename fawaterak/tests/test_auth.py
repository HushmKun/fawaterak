from __future__ import annotations

import threading
import time
from importlib.metadata import version
from platform import python_version, release, system
from typing import Any

import pytest
import requests
import requests_mock

from fawaterak.auth import TokenManager
from fawaterak.exceptions import FawaterakAuthException, FawaterakConnectionException

BASE_URL = "https://api.example.com"
CLIENT_ID = "test-client-id"
CLIENT_SECRET = "test-client-secret"
ACCESS_TOKEN = "access-token-123"
REFRESH_TOKEN = "refresh-token-456"
NEW_REFRESH_TOKEN = "new-refresh-token-789"


def _token_response(
	access_token: str = ACCESS_TOKEN,
	expires_in: int = 300,
	refresh_token: str | None = REFRESH_TOKEN,
) -> dict[str, Any]:
	response: dict[str, Any] = {
		"access_token": access_token,
		"expires_in": expires_in,
	}
	if refresh_token is not None:
		response["refresh_token"] = refresh_token
	return response


class TestTokenManagerInit:
	def test_init_stores_arguments(self) -> None:
		session = requests.Session()
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL, session)
		assert manager._client_id == CLIENT_ID
		assert manager._client_secret == CLIENT_SECRET
		assert manager._base_url == BASE_URL
		assert manager._session is session

	def test_init_strips_trailing_slash_from_base_url(self) -> None:
		manager = TokenManager(
			CLIENT_ID,
			CLIENT_SECRET,
			"https://api.example.com/",
		)
		assert manager._base_url == "https://api.example.com"

	def test_init_initial_state(self) -> None:
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		assert manager._access_token is None
		assert manager._refresh_token is None
		assert manager._expires_at == 0.0

	def test_init_session_headers(self) -> None:
		session = TokenManager._build_session()
		assert isinstance(session, requests.Session)
		assert session.headers["User-Agent"] == (
			f"Fawaterak-sdk-auth/{version('fawaterak')} Python/{python_version()} {system()}/{release()}"
		)


class TestAccessTokenProperty:
	def test_triggers_client_credentials_exchange(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		token = manager.access_token
		assert token == ACCESS_TOKEN
		assert len(requests_mock.request_history) == 1
		request = requests_mock.request_history[0]
		assert request.json() == {
			"grant_type": "client_credentials",
			"client_id": CLIENT_ID,
			"client_secret": CLIENT_SECRET,
		}

	def test_caches_and_does_not_re_request(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(expires_in=300),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		assert manager.access_token == ACCESS_TOKEN
		assert manager.access_token == ACCESS_TOKEN
		assert len(requests_mock.request_history) == 1

	def test_refreshes_when_expired(self, requests_mock: requests_mock.Mocker) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._access_token = "old-token"
		manager._refresh_token = REFRESH_TOKEN
		manager._expires_at = time.time() - 1
		token = manager.access_token
		assert token == ACCESS_TOKEN
		assert len(requests_mock.request_history) == 1
		assert requests_mock.request_history[0].json()["grant_type"] == "refresh_token"

	def test_refreshes_when_no_access_token_but_refresh_token_exists(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		assert manager.access_token == ACCESS_TOKEN
		assert requests_mock.request_history[0].json()["grant_type"] == "refresh_token"

	def test_uses_refresh_token_when_available(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._access_token = "old-token"
		manager._refresh_token = REFRESH_TOKEN
		manager._expires_at = time.time() + 3600
		manager.refresh(force=True)
		assert manager.access_token == ACCESS_TOKEN
		assert requests_mock.request_history[0].json()["grant_type"] == "refresh_token"


class TestRefreshMethod:
	def test_forces_exchange_even_if_token_valid(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._access_token = "old-token"
		manager._refresh_token = REFRESH_TOKEN
		manager._expires_at = time.time() + 3600
		manager.refresh(force=True)
		assert manager._access_token == ACCESS_TOKEN
		assert len(requests_mock.request_history) == 1

	def test_uses_refresh_token_when_available(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager.refresh()
		assert requests_mock.request_history[0].json()["grant_type"] == "refresh_token"


class TestPayloadAndUrl:
	def test_client_credentials_payload(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(f"{BASE_URL}/oauth/token", json=_token_response())
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager.refresh()
		body = requests_mock.request_history[0].json()
		assert body == {
			"grant_type": "client_credentials",
			"client_id": CLIENT_ID,
			"client_secret": CLIENT_SECRET,
		}

	def test_refresh_token_payload(self, requests_mock: requests_mock.Mocker) -> None:
		requests_mock.post(f"{BASE_URL}/oauth/token", json=_token_response())
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager.refresh()
		body = requests_mock.request_history[0].json()
		assert body == {
			"grant_type": "refresh_token",
			"refresh_token": REFRESH_TOKEN,
			"client_id": CLIENT_ID,
			"client_secret": CLIENT_SECRET,
		}

	def test_post_url_has_no_trailing_slash(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(f"{BASE_URL}/oauth/token", json=_token_response())
		manager = TokenManager(
			CLIENT_ID,
			CLIENT_SECRET,
			"https://api.example.com/",
		)
		manager.refresh()
		assert requests_mock.request_history[0].url == f"{BASE_URL}/oauth/token"


class TestResponseParsing:
	def test_parses_access_token_refresh_token_and_expires_in(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(f"{BASE_URL}/oauth/token", json=_token_response())
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager.refresh()
		assert manager._access_token == ACCESS_TOKEN
		assert manager._refresh_token == REFRESH_TOKEN
		assert manager._expires_at > time.time()

	def test_expiry_includes_safety_margin(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(expires_in=300),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager.refresh()
		expected_max = time.time() + 270
		assert manager._expires_at <= expected_max

	def test_retains_existing_refresh_token_if_response_omits_it(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(refresh_token=None),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager.refresh()
		assert manager._refresh_token == REFRESH_TOKEN

	def test_overwrites_refresh_token_if_response_provides_new_one(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(refresh_token=NEW_REFRESH_TOKEN),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager.refresh()
		assert manager._refresh_token == NEW_REFRESH_TOKEN


class TestErrorHandling:
	def test_request_exception_raises_connection_exception(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			exc=requests.exceptions.ConnectTimeout("connection timed out"),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		with pytest.raises(FawaterakConnectionException):
			manager.refresh()

	def test_non_ok_without_refresh_token_raises_auth_exception(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			status_code=400,
			json={"message": "invalid credentials"},
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		with pytest.raises(FawaterakAuthException) as exc_info:
			manager.refresh()
		assert exc_info.value.status_code == 400
		assert exc_info.value.raw_body == {"message": "invalid credentials"}

	def test_non_ok_with_refresh_token_fallback_to_client_credentials(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			[
				{"status_code": 400, "json": {"message": "bad refresh"}},
				{"status_code": 200, "json": _token_response()},
			],
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager._expires_at = time.time() - 1
		token = manager.access_token
		assert token == ACCESS_TOKEN
		assert len(requests_mock.request_history) == 2
		assert (
			requests_mock.request_history[1].json()["grant_type"]
			== "client_credentials"
		)

	def test_non_ok_with_refresh_token_and_client_credentials_fail_raises(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			status_code=401,
			json={"message": "unauthorized"},
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager._access_token = "old-access-token"
		with pytest.raises(FawaterakAuthException) as exc_info:
			manager.refresh()
		assert exc_info.value.status_code == 401
		assert len(requests_mock.request_history) == 2

	def test_non_json_error_response_raises_auth_exception_with_defaults(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			status_code=400,
			text="Internal Server Error",
			headers={"Content-Type": "text/html"},
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		with pytest.raises(FawaterakAuthException) as exc_info:
			manager.refresh()

		assert exc_info.value.status_code == 400
		assert exc_info.value.message == "OAuth token exchange failed"

	def test_error_response_without_message_uses_default(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			status_code=400,
			json={},
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		with pytest.raises(FawaterakAuthException) as exc_info:
			manager.refresh()
		assert exc_info.value.message == "OAuth token exchange failed"


class TestMalformedResponses:
	def test_response_missing_access_token_raises_key_error(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json={"expires_in": 300, "refresh_token": REFRESH_TOKEN},
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		with pytest.raises(KeyError):
			manager.refresh()

	def test_response_missing_expires_in_raises_key_error(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json={"access_token": ACCESS_TOKEN, "refresh_token": REFRESH_TOKEN},
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		with pytest.raises(KeyError):
			manager.refresh()

	def test_expires_in_zero_causes_immediate_expiry(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(expires_in=0),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager.refresh()
		assert manager._expires_at <= time.time()

	def test_negative_expires_in_causes_immediate_expiry(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			json=_token_response(expires_in=-10),
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager.refresh()
		assert manager._expires_at < time.time()


class TestRecursionSafety:
	def test_refresh_token_cleared_before_client_credentials_fallback(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/oauth/token",
			[
				{"status_code": 400, "json": {"message": "bad refresh"}},
				{"status_code": 200, "json": _token_response()},
			],
		)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		manager._refresh_token = REFRESH_TOKEN
		manager._expires_at = time.time() - 1
		manager.access_token  # noqa: B018
		second_request = requests_mock.request_history[1]
		assert second_request.json()["grant_type"] == "client_credentials"
		assert "refresh_token" not in second_request.json()
		assert manager._refresh_token == REFRESH_TOKEN


class TestThreadSafety:
	def test_concurrent_access_token_calls_trigger_single_request(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		call_count = 0
		lock = threading.Lock()

		def slow_response(request: Any, context: Any) -> dict[str, Any]:
			nonlocal call_count
			with lock:
				call_count += 1
			time.sleep(0.1)
			context.headers["Content-Type"] = "application/json"
			return _token_response()

		requests_mock.post(f"{BASE_URL}/oauth/token", json=slow_response)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		results: list[str | None] = []
		result_lock = threading.Lock()

		def fetch() -> None:
			token = manager.access_token
			with result_lock:
				results.append(token)

		threads = [threading.Thread(target=fetch) for _ in range(10)]
		for t in threads:
			t.start()
		for t in threads:
			t.join()

		assert call_count == 1
		assert all(r == ACCESS_TOKEN for r in results)

	def test_concurrent_refresh_calls_serialize(
		self, requests_mock: requests_mock.Mocker
	) -> None:
		call_count = 0
		lock = threading.Lock()

		def slow_response(request: Any, context: Any) -> dict[str, Any]:
			nonlocal call_count
			with lock:
				call_count += 1
			time.sleep(0.1)
			context.headers["Content-Type"] = "application/json"
			return _token_response()

		requests_mock.post(f"{BASE_URL}/oauth/token", json=slow_response)
		manager = TokenManager(CLIENT_ID, CLIENT_SECRET, BASE_URL)
		threads = [threading.Thread(target=manager.refresh) for _ in range(10)]
		for t in threads:
			t.start()
		for t in threads:
			t.join()

		assert call_count == 1
