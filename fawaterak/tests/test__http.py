"""Unit tests for the Fawaterak HTTP client."""

from __future__ import annotations

import json
from typing import Any, cast
from unittest.mock import patch

import pytest
import requests
import requests_mock
from requests.adapters import HTTPAdapter

from fawaterak._http import HTTPClient
from fawaterak.exceptions import (
	FawaterakAPIException,
	FawaterakAuthException,
	FawaterakConnectionException,
	FawaterakTemporaryException,
	FawaterakValidationException,
)
from fawaterak.tests._helpers import FakeTokenManager

BASE_URL = "https://api.example.com"


def _make_response(
	status_code: int = 200,
	json_body: dict[str, Any] | None = None,
	text: str = "",
) -> requests.Response:
	"""Build a real requests.Response standing in for an API response."""
	resp = requests.Response()
	resp.status_code = status_code
	resp.url = f"{BASE_URL}/"
	if json_body is not None:
		resp._content = json.dumps(json_body).encode("utf-8")
		resp.headers["Content-Type"] = "application/json"
	else:
		resp._content = text.encode("utf-8")
	return resp


@pytest.fixture
def token_manager() -> FakeTokenManager:
	return FakeTokenManager()


@pytest.fixture
def client(token_manager: FakeTokenManager) -> HTTPClient:
	return HTTPClient(base_url=BASE_URL, token_manager=token_manager)  # ty: ignore[invalid-argument-type]


class TestHTTPClientInit:
	def test_strips_trailing_slash_from_base_url(
		self, token_manager: FakeTokenManager
	) -> None:
		http_client = HTTPClient(base_url=f"{BASE_URL}/", token_manager=token_manager)  # ty: ignore[invalid-argument-type]
		assert http_client._base_url == BASE_URL
		assert http_client._timeout == 30.0

	def test_keeps_base_url_without_trailing_slash(
		self, token_manager: FakeTokenManager
	) -> None:
		http_client = HTTPClient(
			base_url=BASE_URL,
			token_manager=cast(Any, token_manager),
			timeout=5.0,
		)
		assert http_client._base_url == BASE_URL
		assert http_client._timeout == 5.0

	def test_authorization_header_and_accept_and_content_type_headers(
		self, client: HTTPClient, token_manager: FakeTokenManager
	) -> None:
		assert (
			client._session.headers["Authorization"]
			== f"Bearer {token_manager.access_token}"
		)
		assert client._session.headers["Accept"] == "application/json"
		assert client._session.headers["Content-Type"] == "application/json"

	def test_user_agent_header_shape(self, client: HTTPClient) -> None:
		ua = client._session.headers["User-Agent"]
		assert ua.startswith("Fawaterak-sdk/")
		assert "Python/" in ua

	def test_adapters_mounted_for_http_and_https(self, client: HTTPClient) -> None:
		assert "http://" in client._session.adapters
		assert "https://" in client._session.adapters

	def test_transport_retry_only_applies_to_get(self, client: HTTPClient) -> None:
		adapter = cast(HTTPAdapter, client._session.get_adapter(BASE_URL))
		assert adapter.max_retries.allowed_methods == frozenset({"GET"})

	def test_transport_retry_status_forcelist_is_503_only(
		self, client: HTTPClient
	) -> None:
		adapter = cast(HTTPAdapter, client._session.get_adapter(BASE_URL))
		assert adapter.max_retries.status_forcelist == (503,)

	def test_transport_retry_total_is_three(self, client: HTTPClient) -> None:
		adapter = cast(HTTPAdapter, client._session.get_adapter(BASE_URL))
		assert adapter.max_retries.total == 3

	def test_each_client_gets_its_own_session(
		self, token_manager: FakeTokenManager
	) -> None:
		c1 = HTTPClient(base_url=BASE_URL, token_manager=token_manager)  # ty: ignore[invalid-argument-type]
		c2 = HTTPClient(base_url=BASE_URL, token_manager=token_manager)  # ty: ignore[invalid-argument-type]
		assert c1._session is not c2._session


class TestSuccessfulRequests:
	def test_get_returns_decoded_json(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/transactions/123",
			json={"id": "123", "status": "paid"},
		)
		result = client.request("GET", "/transactions/123")
		request = requests_mock.request_history[0]
		assert result == {"id": "123", "status": "paid"}
		assert request.method == "GET"
		assert request.url == f"{BASE_URL}/transactions/123"

	def test_post_sends_json_body_and_returns_decoded_response(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		payload = {"amount": 100, "currency": "EGP"}
		requests_mock.post(
			f"{BASE_URL}/transactions", status_code=201, json={"id": "new"}
		)
		result = client.request("POST", "/transactions", json=payload)
		assert result == {"id": "new"}
		assert requests_mock.request_history[-1].json() == payload

	def test_query_params_are_forwarded(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(f"{BASE_URL}/transactions", json={"data": []})
		client.request("GET", "/transactions", params={"page": 2, "per_page": 50})
		assert requests_mock.request_history[-1].qs == {
			"page": ["2"],
			"per_page": ["50"],
		}

	def test_url_is_base_url_plus_path(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(f"{BASE_URL}/foo/bar", json={})
		client.request("GET", "/foo/bar")
		assert requests_mock.request_history[-1].url == f"{BASE_URL}/foo/bar"

	def test_configured_timeout_is_used(self, token_manager: FakeTokenManager) -> None:
		http_client = HTTPClient(
			base_url=BASE_URL,
			token_manager=cast(Any, token_manager),
			timeout=7.5,
		)
		resp = _make_response(200, json_body={})
		with patch.object(
			http_client._session, "request", return_value=resp
		) as mock_req:
			http_client.request("GET", "/x")
		assert mock_req.call_args.kwargs["timeout"] == 7.5

	def test_2xx_with_non_json_body_raises_api_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(f"{BASE_URL}/broken", text="<html>not json</html>")
		with pytest.raises(FawaterakAPIException) as exc_info:
			client.request("GET", "/broken")
		assert "non-JSON 2xx" in str(exc_info.value)
		assert exc_info.value.raw_body == {"raw_text": "<html>not json</html>"}


class TestConnectionFailures:
	def test_connection_error_raises_connection_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/anything", exc=requests.exceptions.ConnectionError("boom")
		)
		with pytest.raises(FawaterakConnectionException):
			client.request("GET", "/anything")

	def test_timeout_raises_connection_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/anything", exc=requests.exceptions.Timeout("timed out")
		)
		with pytest.raises(FawaterakConnectionException):
			client.request("GET", "/anything")

	def test_connection_exception_message_preserves_original_error(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/anything",
			exc=requests.exceptions.ConnectionError("DNS lookup failed"),
		)
		with pytest.raises(FawaterakConnectionException) as exc_info:
			client.request("GET", "/anything")
		assert "DNS lookup failed" in str(exc_info.value)

	def test_connection_error_chains_original_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		original = requests.exceptions.ConnectionError("boom")
		requests_mock.get(f"{BASE_URL}/anything", exc=original)
		with pytest.raises(FawaterakConnectionException) as exc_info:
			client.request("GET", "/anything")
		assert exc_info.value.__cause__ is original


class TestAuthRefreshFlow:
	def test_401_then_success_refreshes_token_and_retries_once(
		self,
		client: HTTPClient,
		token_manager: FakeTokenManager,
		requests_mock: requests_mock.Mocker,
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/me",
			[
				{"status_code": 401, "json": {"message": "expired"}},
				{"status_code": 200, "json": {"ok": True}},
			],
		)
		result = client.request("GET", "/me")
		assert result == {"ok": True}
		assert len(requests_mock.request_history) == 2
		assert token_manager.refresh_count == 1

	def test_401_twice_raises_auth_exception_without_infinite_retry(
		self,
		client: HTTPClient,
		token_manager: FakeTokenManager,
		requests_mock: requests_mock.Mocker,
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/me",
			[
				{"status_code": 401, "json": {"message": "still expired"}},
				{"status_code": 401, "json": {"message": "still expired"}},
			],
		)
		with pytest.raises(FawaterakAuthException):
			client.request("GET", "/me")
		# Original call + exactly one retry, never more.
		assert len(requests_mock.request_history) == 2
		assert token_manager.refresh_count == 1

	def test_retry_reuses_same_method_path_json_and_params(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/transactions",
			[
				{"status_code": 401, "json": {}},
				{"status_code": 200, "json": {"ok": True}},
			],
		)
		client.request("POST", "/transactions", json={"a": 1}, params={"b": 2})
		first_call, second_call = requests_mock.request_history
		assert first_call.method == "POST"
		assert second_call.method == "POST"
		assert first_call.qs == second_call.qs == {"b": ["2"]}
		assert second_call.json() == {"a": 1}

	def test_401_auth_exception_carries_status_code_and_body(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		body = {"message": "token expired"}
		requests_mock.get(f"{BASE_URL}/me", status_code=401, json=body)
		with pytest.raises(FawaterakAuthException) as exc_info:
			client.request("GET", "/me")
		assert exc_info.value.status_code == 401
		assert exc_info.value.raw_body == body

	def test_session_authorization_header_is_updated_after_refresh(
		self,
		client: HTTPClient,
		token_manager: FakeTokenManager,
		requests_mock: requests_mock.Mocker,
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/me",
			[
				{"status_code": 401, "json": {}},
				{"status_code": 200, "json": {"ok": True}},
			],
		)
		original_header = client._session.headers["Authorization"]
		client.request("GET", "/me")
		new_header = client._session.headers["Authorization"]
		assert new_header != original_header
		assert new_header == f"Bearer {token_manager.access_token}"

	def test_retried_request_is_sent_with_the_new_bearer_token(
		self,
		client: HTTPClient,
		token_manager: FakeTokenManager,
		requests_mock: requests_mock.Mocker,
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/me",
			[
				{"status_code": 401, "json": {}},
				{"status_code": 200, "json": {"ok": True}},
			],
		)
		client.request("GET", "/me")
		first_call, second_call = requests_mock.request_history
		assert first_call.headers["Authorization"] == "Bearer test-token"
		assert (
			second_call.headers["Authorization"]
			== f"Bearer {token_manager.access_token}"
		)
		assert (
			first_call.headers["Authorization"] != second_call.headers["Authorization"]
		)


class TestErrorStatusMapping:
	@pytest.mark.parametrize("status_code", [400, 422])
	def test_400_and_422_raise_validation_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker, status_code: int
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/transactions",
			status_code=status_code,
			json={"message": "bad field"},
		)
		with pytest.raises(FawaterakValidationException) as exc_info:
			client.request("POST", "/transactions", json={})
		assert exc_info.value.status_code == status_code
		assert exc_info.value.message == "bad field"

	def test_503_raises_temporary_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/health", status_code=503, json={"message": "try later"}
		)
		with pytest.raises(FawaterakTemporaryException) as exc_info:
			client.request("GET", "/health")
		assert exc_info.value.status_code == 503
		assert exc_info.value.message == "try later"

	@pytest.mark.parametrize("status_code", [402, 403, 404, 409, 429, 500, 502])
	def test_other_non_2xx_statuses_raise_generic_api_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker, status_code: int
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/whatever",
			status_code=status_code,
			json={"message": "something else"},
		)
		with pytest.raises(FawaterakAPIException) as exc_info:
			client.request("GET", "/whatever")
		assert exc_info.value.status_code == status_code

	def test_error_body_without_message_key_falls_back_to_response_text(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/whatever", status_code=400, json={"error_code": "X1"}
		)
		with pytest.raises(FawaterakValidationException) as exc_info:
			client.request("GET", "/whatever")
		assert exc_info.value.message == '{"error_code": "X1"}'

	def test_error_body_that_is_not_json_falls_back_to_response_text(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/whatever", status_code=500, text="<html>500 error</html>"
		)
		with pytest.raises(FawaterakAPIException) as exc_info:
			client.request("GET", "/whatever")
		assert exc_info.value.message == "<html>500 error</html>"
		assert exc_info.value.raw_body == {}

	def test_full_error_body_is_attached_to_exception(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		body = {"message": "bad", "errors": {"amount": ["required"]}}
		requests_mock.post(f"{BASE_URL}/transactions", status_code=422, json=body)
		with pytest.raises(FawaterakValidationException) as exc_info:
			client.request("POST", "/transactions", json={})
		assert exc_info.value.raw_body == body

	def test_empty_json_error_body_falls_back_to_text_even_with_message_key_absent(
		self, client: HTTPClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(f"{BASE_URL}/whatever", status_code=400, json={})
		with pytest.raises(FawaterakValidationException) as exc_info:
			client.request("GET", "/whatever")
		assert exc_info.value.message == "{}"


class TestDecodeHelpers:
	def test_decode_or_raise_returns_parsed_json(self, client: HTTPClient) -> None:
		resp = _make_response(200, json_body={"a": 1})
		assert client._decode_or_raise(resp) == {"a": 1}

	def test_decode_or_raise_raises_on_invalid_json(self, client: HTTPClient) -> None:
		resp = _make_response(200, json_body=None, text="not json")
		with pytest.raises(FawaterakAPIException):
			client._decode_or_raise(resp)

	def test_decode_returns_dict_on_valid_json(self, client: HTTPClient) -> None:
		resp = _make_response(400, json_body={"message": "x"})
		assert client._decode(resp) == {"message": "x"}

	def test_decode_returns_empty_dict_on_invalid_json_without_raising(
		self, client: HTTPClient
	) -> None:
		resp = _make_response(400, json_body=None, text="not json")
		assert client._decode(resp) == {}
