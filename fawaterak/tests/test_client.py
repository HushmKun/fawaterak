"""Unit and integration tests for FawaterakClient."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import pytest
import requests
import requests_mock

from fawaterak._http import HTTPClient
from fawaterak.client import FawaterakClient
from fawaterak.config import Config
from fawaterak.models.common import CartItem, Customer, RedirectionUrls
from fawaterak.models.transaction import (
	CardPaymentResult,
	DirectPaymentResult,
	HostedCheckoutResult,
	MobileWalletResult,
	ReferenceCodeResult,
	UnknownPaymentResult,
)

BASE_URL = "https://api.example.com"


class FakeTokenManager:
	"""Token manager stub that avoids real OAuth calls in unit tests."""

	@property
	def access_token(self) -> str:
		return "test-token"

	def refresh(self) -> None:
		pass


@pytest.fixture
def client() -> FawaterakClient:
	config = Config.resolve(
		client_id="test-client-id",
		client_secret="test-client-secret",
		base_url=BASE_URL,
	)
	http_client = HTTPClient(config.base_url, FakeTokenManager())  # ty: ignore[invalid-argument-type]
	return FawaterakClient(config=config, http_client=http_client)


class TestGetPaymentMethods:
	def test_returns_parsed_payment_methods(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/api/v3/getTrPaymentmethods",
			json={
				"status": "success",
				"vendorSettingsData": {"custome_iframe_title": None},
				"data": [
					{
						"payment_method_id": 2,
						"name_en": "Visa-Mastercard",
						"name_ar": "فيزا -ماستر كارد",
						"redirect": "true",
						"logo": "https://example.com/card.png",
						"commission_on_customer": 2,
						"integration_status": 1,
					},
					{
						"payment_method_id": 3,
						"name_en": "Fawry",
						"name_ar": "فوري",
						"redirect": "false",
						"logo": "https://example.com/fawry.png",
						"commission_on_customer": 2,
						"integration_status": 1,
					},
				],
			},
		)
		methods = client.get_payment_methods()
		assert len(methods) == 2
		assert methods[0].payment_method_id == 2
		assert methods[0].redirect is True
		assert methods[1].name_en == "Fawry"
		assert methods[1].redirect is False


class TestCreateTransaction:
	def test_hosted_checkout_returns_url(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createTransaction",
			json={
				"status": "success",
				"message": "Transaction link created",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"url": "https://app.fawaterk.com/ts/a1b2c",
					"short_url": "https://fawaterk.com/a1b2c",
					"short_code": "a1b2c",
					"expires_in": 2592000,
				},
			},
		)
		result = client.create_transaction(
			currency="EGP",
			customer=Customer(first_name="Ahmed", last_name="Ali"),
			cart_items=[CartItem(name="Order", price=100.0, quantity=1)],
			cart_total=100.0,
		)
		assert isinstance(result, HostedCheckoutResult)
		assert result.intent_key == "550e8400-e29b-41d4-a716-446655440000"
		assert result.url == "https://app.fawaterk.com/ts/a1b2c"
		assert result.short_code == "a1b2c"

	def test_direct_card_returns_card_result(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createTransaction",
			json={
				"status": "success",
				"message": "Transaction link created",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"expires_in": 2592000,
					"payment_data": {
						"redirectTo": "https://staging.fawaterk.com/link/I0PAH"
					},
				},
			},
		)
		result = client.create_transaction(
			currency="EGP",
			customer=Customer(first_name="Ahmed", last_name="Ali"),
			cart_items=[CartItem(name="Order", price=100.0, quantity=1)],
			cart_total=100.0,
			payment_method_id=2,
		)
		assert isinstance(result, DirectPaymentResult)
		assert isinstance(result.payment_data, CardPaymentResult)
		assert (
			result.payment_data.redirect_to == "https://staging.fawaterk.com/link/I0PAH"
		)

	def test_direct_fawry_returns_reference_code_result(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createTransaction",
			json={
				"status": "success",
				"message": "Transaction link created",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"expires_in": 2592000,
					"payment_data": {
						"referenceNumber": "981335305",
						"expireDate": "2021-07-06 15:53:41",
						"expirationTime": "2021-07-06 15:53:41",
					},
				},
			},
		)
		result = client.create_transaction(
			currency="EGP",
			customer=Customer(first_name="Ahmed", last_name="Ali"),
			cart_items=[CartItem(name="Order", price=100.0, quantity=1)],
			cart_total=100.0,
			payment_method_id=3,
		)
		assert isinstance(result, DirectPaymentResult)
		assert isinstance(result.payment_data, ReferenceCodeResult)
		assert result.payment_data.reference_number == "981335305"

	def test_direct_mobile_wallet_returns_wallet_result(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createTransaction",
			json={
				"status": "success",
				"message": "Transaction link created",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"expires_in": 2592000,
					"payment_data": {
						"systemReference": "4266311",
						"isoQr": "00020101021226330016A00000073210000101096100559795204152053038185406106",
					},
				},
			},
		)
		result = client.create_transaction(
			currency="EGP",
			customer=Customer(first_name="Ahmed", last_name="Ali"),
			cart_items=[CartItem(name="Order", price=100.0, quantity=1)],
			cart_total=100.0,
			payment_method_id=4,
		)
		assert isinstance(result, DirectPaymentResult)
		assert isinstance(result.payment_data, MobileWalletResult)
		assert result.payment_data.system_reference == "4266311"

	def test_unknown_payment_data_returns_raw_result(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createTransaction",
			json={
				"status": "success",
				"message": "Transaction link created",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"expires_in": 2592000,
					"payment_data": {"unexpectedKey": "value"},
				},
			},
		)
		result = client.create_transaction(
			currency="EGP",
			customer=Customer(first_name="Ahmed", last_name="Ali"),
			cart_items=[CartItem(name="Order", price=100.0, quantity=1)],
			cart_total=100.0,
			payment_method_id=99,
		)
		assert isinstance(result, DirectPaymentResult)
		assert isinstance(result.payment_data, UnknownPaymentResult)
		assert result.payment_data.raw == {"unexpectedKey": "value"}

	def test_request_payload_includes_optional_fields(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createTransaction",
			json={
				"status": "success",
				"message": "Transaction link created",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"url": "https://app.fawaterk.com/ts/a1b2c",
					"expires_in": 2592000,
				},
			},
		)
		client.create_transaction(
			currency="SAR",
			customer=Customer(
				first_name="Ahmed",
				last_name="Ali",
				email="ahmed@example.com",
				customer_unique_id="user_12345",
			),
			cart_items=[CartItem(name="Order", price=100.0, quantity=1)],
			cart_total=100.0,
			save_customer=True,
			pay_load={"order_id": "ORD-1001"},
			redirection_urls=RedirectionUrls(
				success_url="https://example.com/success",
				fail_url="https://example.com/fail",
			),
			send_email=True,
			due_date="2026-06-08T12:00:00Z",
			tr_number="TR-1001",
			list_style="v",
			lang="ar",
		)
		request = requests_mock.request_history[0]
		payload = request.json()
		assert payload["currency"] == "SAR"
		assert payload["save_customer"] is True
		assert payload["customer"]["customer_unique_id"] == "user_12345"
		assert payload["pay_load"] == {"order_id": "ORD-1001"}
		assert payload["redirectionUrls"] == {
			"success_url": "https://example.com/success",
			"fail_url": "https://example.com/fail",
		}
		assert payload["sendEmail"] is True
		assert payload["due_date"] == "2026-06-08T12:00:00Z"
		assert payload["tr_number"] == "TR-1001"
		assert payload["list_style"] == "v"
		assert payload["lang"] == "ar"


class TestGetTransaction:
	def test_returns_transaction_data(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/getTransactionData",
			json={
				"status": "success",
				"data": {
					"intent_key": "550e8400-e29b-41d4-a716-446655440000",
					"transaction_id": 12345,
					"customer_email": "ahmed@example.com",
					"commission": 2.5,
					"transaction_created_at": "2026-06-06 12:00:00",
					"paid": 1,
					"paid_at": "2026-06-06 12:05:00",
					"status_text": "paid",
					"total": 100,
					"currency": "EGP",
					"payment_method": "Fawry",
					"pay_load": {"order_id": "ORD-1001"},
					"due_date": "2026-06-08 12:00:00",
					"transaction_link": "https://app.fawaterk.com/transactions/550e8400",
					"transaction_history": [
						{
							"method": {
								"name": "Fawry",
								"logo": "https://example.com/fawry.png",
							},
							"amount": "100.00 EGP",
							"currency": "EGP",
							"status": "success",
							"reference": "981335305",
							"date": "2026-06-06 12:05:00",
						}
					],
				},
			},
		)
		result = client.get_transaction("550e8400-e29b-41d4-a716-446655440000")
		assert result.intent_key == "550e8400-e29b-41d4-a716-446655440000"
		assert result.transaction_id == 12345
		assert result.paid == 1
		assert result.status_text == "paid"
		assert len(result.transaction_history) == 1
		assert result.transaction_history[0].method_name == "Fawry"


class TestListTransactions:
	def test_returns_paginated_results(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/api/v3/getTransactionsData",
			json={
				"status": "success",
				"data": [
					{
						"transaction_id": 12345,
						"intent_key": "550e8400-e29b-41d4-a716-446655440000",
						"invoice_id": 678,
						"customer_email": "ahmed@example.com",
						"transaction_created_at": "2026-06-06 12:00:00",
						"status_text": "paid",
						"total": 100,
						"currency": "EGP",
						"pay_load": {"order_id": "ORD-1001"},
						"payment_method": "Fawry",
						"transaction_transactions": [],
						"original_amount_egp": 100.0,
					}
				],
				"pagination": {
					"total": 1,
					"per_page": 15,
					"current_page": 1,
					"last_page": 1,
					"from": 1,
					"to": 1,
				},
			},
		)
		result = client.list_transactions(
			start_date=date(2026, 1, 1),
			end_date=date(2026, 1, 31),
		)
		assert len(result.data) == 1
		assert result.total == 1
		assert result.current_page == 1
		assert result.data[0].transaction_id == 12345

	def test_query_params_include_pay_load_filter(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.get(
			f"{BASE_URL}/api/v3/getTransactionsData",
			json={"status": "success", "data": [], "pagination": {}},
		)
		client.list_transactions(
			start_date="2026-01-01",
			end_date="2026-01-31",
			page=2,
			per_page=20,
			pay_load="ORD-1001",
		)
		request = requests_mock.request_history[0]
		assert request.qs["start_date"] == ["2026-01-01"]
		assert request.qs["end_date"] == ["2026-01-31"]
		assert request.qs["page"] == ["2"]
		assert request.qs["per_page"] == ["20"]
		assert "pay_load=ORD-1001" in request.url


@pytest.mark.integration
class TestStagingIntegration:
	"""Live smoke tests against Fawaterak staging. Run with real credentials."""

	@pytest.fixture(autouse=True)
	def clean_env(self) -> None:
		"""Override conftest's clean_env — these tests need real credentials."""
		pass

	@pytest.fixture
	def staging_client(self) -> FawaterakClient:
		if not all(
			os.environ.get(var)
			for var in ("FAWATERAK_CLIENT_ID", "FAWATERAK_CLIENT_SECRET")
		):
			pytest.skip("Staging credentials not set")
		config = Config.resolve()
		return FawaterakClient(config=config)

	def test_get_payment_methods_and_create_transaction(
		self, staging_client: FawaterakClient
	) -> None:
		methods = staging_client.get_payment_methods()
		assert len(methods) > 0

		result = staging_client.create_transaction(
			currency="EGP",
			customer=Customer(
				first_name="Integration",
				last_name="Test",
				email="integration@example.com",
			),
			cart_items=[CartItem(name="Test order", price=100.0, quantity=1)],
			cart_total=100.0,
			redirection_urls=RedirectionUrls(
				success_url="https://example.com/success",
				fail_url="https://example.com/fail",
			),
		)
		assert result.intent_key
		if isinstance(result, HostedCheckoutResult):
			assert result.url.startswith("http")
		else:
			assert result.payment_data is not None
