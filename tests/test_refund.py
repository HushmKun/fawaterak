"""Unit and integration tests for the Refunds surface of FawaterakClient."""

from __future__ import annotations

import os

import pytest
import requests_mock

from fawaterak._http import HTTPClient
from fawaterak.client import FawaterakClient
from fawaterak.config import Config
from fawaterak.exceptions import FawaterakValidationException
from fawaterak.models.refund import (
	RefundCreationResult,
	RefundRequest,
	RefundType,
)
from fawaterak.models.transaction import Page

BASE_URL = "https://api.example.com"

# Shapes captured live from staging on 2026-10-16.
REFUND_TYPES_RESPONSE = {
	"status": "success",
	"data": {
		"0": "invoice",
		"1": "Payment link transaction",
		"2": "Collection link transaction",
		"3": "Integration transaction",
	},
}

REFUND_REASONS_RESPONSE = {
	"status": "success",
	"data": [
		"Product not available",
		"Customer changed their mind",
		"Incorrect product delivered",
		"Other",
	],
}

CREATE_REFUND_RESPONSE = {"status": "success", "message": "Refunded successfully"}

# Flat paginator (no nested "data" wrapper like e-invoice list index).
REFUND_INDEX_RESPONSE = {
	"current_page": 1,
	"data": [
		{
			"id": 827,
			"refundable_type": "Transaction",
			"refundable_amount": "1",  # string on the wire
			"status": "approved",
			"refundable_id": 3485,
			"reason": "Customer changed their mind",
			"created_at": "2026-10-16T17:15:45.000000Z",
			"can_delete": False,
		}
	],
	"first_page_url": "https://staging.fawaterk.com/api/v3/refund/index?page=1",
	"from": 1,
	"last_page": 1,
	"last_page_url": "https://staging.fawaterk.com/api/v3/refund/index?page=1",
	"next_page_url": None,
	"path": "https://staging.fawaterk.com/api/v3/refund/index",
	"per_page": 10,
	"prev_page_url": None,
	"to": 1,
	"total": 1,
}

REFUND_EMPTY_INDEX_RESPONSE = {
	"current_page": 1,
	"data": [],
	"first_page_url": "https://staging.fawaterk.com/api/v3/refund/index?page=1",
	"from": None,
	"last_page": 1,
	"last_page_url": "https://staging.fawaterk.com/api/v3/refund/index?page=1",
	"next_page_url": None,
	"path": "https://staging.fawaterk.com/api/v3/refund/index",
	"per_page": 10,
	"prev_page_url": None,
	"to": None,
	"total": 0,
}

# Bare object: no {"status": ..., "data": ...} wrapper for details.
REFUND_DETAILS_RESPONSE = {
	"id": 827,
	"refundable_amount": "1",
	"status": "approved",
	"reason": "Customer changed their mind",
	"created_at": "2026-10-16T17:15:45.000000Z",
}


@pytest.fixture
def client() -> FawaterakClient:
	config = Config.resolve(
		client_id="test-client-id",
		client_secret="test-client-secret",
		base_url=BASE_URL,
	)
	from _helpers import FakeTokenManager

	http_client = HTTPClient(config.base_url, FakeTokenManager())  # ty: ignore[invalid-argument-type]
	return FawaterakClient(config=config, http_client=http_client)


class TestGetRefundTypes:
	def test_labels_types_by_code(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/refundTypes", json=REFUND_TYPES_RESPONSE
		)
		result = client.get_refund_types()
		assert result == {
			"0": "invoice",
			"1": "Payment link transaction",
			"2": "Collection link transaction",
			"3": "Integration transaction",
		}
		assert requests_mock.request_history[0].json() == {"lang": "en"}

	def test_passes_lang(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/refundTypes", json=REFUND_TYPES_RESPONSE
		)
		client.get_refund_types(lang="ar")
		last = requests_mock.request_history[0]
		assert last.json()["lang"] == "ar"


class TestGetRefundReasons:
	def test_returns_reason_strings(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/refundReasons", json=REFUND_REASONS_RESPONSE
		)
		result = client.get_refund_reasons()
		assert result == REFUND_REASONS_RESPONSE["data"]
		assert requests_mock.request_history[0].json() == {"lang": "en"}


class TestCreateRefund:
	@pytest.mark.parametrize(
		("refund_type", "expected_enum"),
		[
			(RefundType.INTEGRATION_TRANSACTION, RefundType.INTEGRATION_TRANSACTION),
			(3, RefundType.INTEGRATION_TRANSACTION),
			("3", RefundType.INTEGRATION_TRANSACTION),
		],
	)
	def test_accepts_enum_int_and_str(
		self,
		client: FawaterakClient,
		requests_mock: requests_mock.Mocker,
		refund_type: RefundType | int | str,
		expected_enum: RefundType,
	) -> None:
		assert expected_enum is RefundType.INTEGRATION_TRANSACTION
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/create", json=CREATE_REFUND_RESPONSE
		)
		result = client.create_refund(
			refund_type=refund_type,
			refund_id=3485,
			reason="Customer changed their mind",
			refundable_amount=1.0,
			comment="SDK Phase 4 staging smoke test",
		)

		assert isinstance(result, RefundCreationResult)
		assert result.message == "Refunded successfully"
		last = requests_mock.request_history[0]
		assert last.json() == {
			"refund_type": "3",
			"refund_id": 3485,
			"reason": "Customer changed their mind",
			"refundable_amount": 1.0,
			"comment": "SDK Phase 4 staging smoke test",
		}

	def test_omits_comment_when_not_given(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/create", json=CREATE_REFUND_RESPONSE
		)
		result = client.create_refund(
			refund_type=RefundType.INVOICE,
			refund_id=1105654,
			reason="Other",
			refundable_amount=50,
		)
		assert result.status == "success"
		assert requests_mock.request_history[0].json() == {
			"refund_type": "0",
			"refund_id": 1105654,
			"reason": "Other",
			"refundable_amount": 50,
		}

	def test_rejects_unknown_refund_type(self, client: FawaterakClient) -> None:
		with pytest.raises(FawaterakValidationException):
			client.create_refund(
				refund_type="bogus",
				refund_id=1,
				reason="Other",
				refundable_amount=1.0,
			)


class TestListRefunds:
	def test_returns_paginated_refund_requests(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/index", json=REFUND_INDEX_RESPONSE
		)
		result = client.list_refunds()

		assert isinstance(result, Page)
		assert result.total == 1
		assert result.per_page == 10
		assert result.current_page == 1
		assert result.last_page == 1
		assert result.from_item == 1
		assert result.to_item == 1

		[record] = result.data
		assert isinstance(record, RefundRequest)
		assert record.id == 827
		assert record.refundable_type == "Transaction"
		assert record.refundable_amount == 1.0  # parsed from string "1"
		assert record.refundable_id == 3485
		assert record.status == "approved"
		assert record.reason == "Customer changed their mind"
		assert record.created_at == "2026-10-16T17:15:45.000000Z"
		assert record.can_delete is False

	def test_passes_page_in_body(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/index", json=REFUND_INDEX_RESPONSE
		)
		client.list_refunds(page=2)
		assert requests_mock.request_history[0].json() == {"page": 2}

	def test_returns_empty_page_when_no_refunds(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/index", json=REFUND_EMPTY_INDEX_RESPONSE
		)
		result = client.list_refunds()
		assert isinstance(result, Page)
		assert result.data == []
		assert result.total == 0
		assert result.from_item is None
		assert result.to_item is None


class TestGetRefund:
	def test_returns_details_from_bare_object(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/api/v3/refund/details/827", json=REFUND_DETAILS_RESPONSE
		)
		result = client.get_refund(827)

		assert isinstance(result, RefundRequest)
		assert result.id == 827
		assert result.refundable_amount == 1.0
		assert result.status == "approved"
		assert result.reason == "Customer changed their mind"
		# List-only fields degrade to None for the details response.
		assert result.refundable_type is None
		assert result.refundable_id is None
		assert result.can_delete is None

	def test_returns_none_for_empty_object(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		# Staging returns {} (HTTP 200) for a refund id that does not exist.
		requests_mock.get(
			f"{BASE_URL}/api/v3/refund/details/999999999", status_code=200, json={}
		)
		assert client.get_refund(999999999) is None

	def test_returns_none_for_body_without_id(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/api/v3/refund/details/827",
			status_code=200,
			json={"status": "error", "message": "Refund not found"},
		)
		assert client.get_refund(827) is None

	@pytest.mark.parametrize(
		"refund_id",
		[
			"827?page=2",
			"1/../../invoice",
			"827#frag",
			"..",
			"a12",
			"12312.0",
			3.9,
			True,
			None,
		],
	)
	def test_rejects_unsafe_refund_id_without_request(
		self,
		client: FawaterakClient,
		requests_mock: requests_mock.Mocker,
		refund_id: object,
	) -> None:
		with pytest.raises(FawaterakValidationException) as exc_info:
			client.get_refund(refund_id)  # ty: ignore[invalid-argument-type]
		assert exc_info.value.status_code == 400
		assert requests_mock.call_count == 0

	def test_accepts_numeric_string_id(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/api/v3/refund/details/827", json=REFUND_DETAILS_RESPONSE
		)
		assert client.get_refund("827").id == 827  # ty: ignore[invalid-argument-type, unresolved-attribute]


class TestDeleteRefund:
	def test_deletes_pending_request(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/refund/delete",
			json={"status": "success"},
			status_code=200,
		)
		assert client.delete_refund(42) is True
		assert requests_mock.request_history[0].json() == {"refund_id": 42}


@pytest.mark.integration
class TestRefundStagingIntegration:
	"""Live refund tests against Fawaterak staging. Run with real credentials."""

	@pytest.fixture(autouse=True)
	def clean_env(self) -> None:
		"""Override conftest's clean_env — these tests need real credentials."""

	@pytest.fixture
	def staging_client(self) -> FawaterakClient:
		if not all(
			os.environ.get(var)
			for var in ("FAWATERAK_CLIENT_ID", "FAWATERAK_CLIENT_SECRET")
		):
			pytest.skip("Staging credentials not set")
		return FawaterakClient(config=Config.resolve(environment="staging"))

	@pytest.fixture
	def paid_transaction_id(self, staging_client: FawaterakClient) -> int:
		"""Find one paid transaction to refund; refunds least amount possible."""
		page = staging_client.list_transactions(
			start_date="2026-08-01", end_date="2026-12-31"
		)
		paid = [item for item in page.data if item.status_text == "paid"]
		if not paid:
			pytest.skip("No paid transaction available on this staging account")
		paid.sort(key=lambda item: item.total)
		return paid[0].transaction_id

	def test_get_refund_types(self, staging_client: FawaterakClient) -> None:
		types = staging_client.get_refund_types()
		assert types == {
			"0": "invoice",
			"1": "Payment link transaction",
			"2": "Collection link transaction",
			"3": "Integration transaction",
		}

	def test_get_refund_reasons(self, staging_client: FawaterakClient) -> None:
		reasons = staging_client.get_refund_reasons()
		assert "Customer changed their mind" in reasons

	def test_list_refunds(self, staging_client: FawaterakClient) -> None:
		page = staging_client.list_refunds()
		assert isinstance(page, Page)
		for record in page.data:
			assert record.id > 0
			assert record.refundable_amount >= 1

	def test_create_refund_and_poll_status(
		self, staging_client: FawaterakClient, paid_transaction_id: int
	) -> None:
		result = staging_client.create_refund(
			refund_type=RefundType.INTEGRATION_TRANSACTION,
			refund_id=paid_transaction_id,
			reason="Customer changed their mind",
			refundable_amount=1.0,
			comment="pytest integration run",
		)
		assert isinstance(result, RefundCreationResult)
		assert result.status == "success"

		found = [
			record
			for page in self._all_refund_pages(staging_client)
			for record in page.data
			if record.refundable_id == paid_transaction_id
		]
		assert found, "refund request should appear in list_refunds"
		record = found[0]
		assert record.refundable_amount == 1.0
		# Staging auto-approves instantly; production would start as "pending".
		assert record.status in ("pending", "approved")

		# details endpoint must return the same record
		fetched = staging_client.get_refund(record.id)
		assert fetched is not None
		assert fetched.id == record.id
		assert fetched.refundable_amount == 1.0

		# If still pending (can_delete), cancel it to keep the account clean
		if record.can_delete:
			assert staging_client.delete_refund(record.id) is True

	@staticmethod
	def _all_refund_pages(staging_client: FawaterakClient) -> list[Page[RefundRequest]]:
		pages = []
		page = staging_client.list_refunds(page=1)
		current = page.current_page
		while current <= page.last_page:
			pages.append(staging_client.list_refunds(page=current))
			current += 1
		return pages
