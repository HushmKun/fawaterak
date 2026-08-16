"""Unit and integration tests for FawaterakClient."""

from __future__ import annotations

import os
import uuid
from datetime import date

import pytest
import requests_mock
from _helpers import FakeTokenManager

from fawaterak._http import HTTPClient
from fawaterak.client import FawaterakClient
from fawaterak.config import Config
from fawaterak.exceptions import (
	FawaterakConfigException,
	FawaterakValidationException,
	FawaterakWebhookException,
)
from fawaterak.models.common import CartItem, Customer, RedirectionUrls
from fawaterak.models.einvoice import (
	EInvoice,
	EinvoiceCreationResult,
	EinvoiceFilter,
)
from fawaterak.models.transaction import (
	CardPaymentResult,
	DirectPaymentResult,
	HostedCheckoutResult,
	MobileWalletResult,
	ReferenceCodeResult,
	UnknownPaymentResult,
)
from fawaterak.webhooks import (
	RefundWebhookEvent,
	WebhookType,
)

BASE_URL = "https://api.example.com"


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


class TestClientWebhooks:
	VENDOR_KEY = "test-vendor-key"

	@pytest.fixture
	def webhook_client(self) -> FawaterakClient:
		config = Config.resolve(
			client_id="test-client-id",
			client_secret="test-client-secret",
			base_url=BASE_URL,
			vendor_api_key=self.VENDOR_KEY,
		)
		http_client = HTTPClient(config.base_url, FakeTokenManager())  # ty: ignore[invalid-argument-type]
		return FawaterakClient(config=config, http_client=http_client)

	def _hmac(self, message: str) -> str:
		import hashlib
		import hmac

		return hmac.new(
			self.VENDOR_KEY.encode("utf-8"),
			message.encode("utf-8"),
			hashlib.sha256,
		).hexdigest()

	def test_parse_paid_webhook_uses_config_vendor_key(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"status": "paid",
		}
		string_to_sign = (
			"TransactionId=12345"
			"&TransactionKey=550e8400-e29b-41d4-a716-446655440000"
			"&PaymentMethod=Visa-Mastercard"
		)
		payload["transactionHashKey"] = self._hmac(string_to_sign)
		event = webhook_client.parse_paid_webhook(payload)

		assert event.status == "paid"
		assert event.transaction_id == 12345
		assert event.transaction_key == "550e8400-e29b-41d4-a716-446655440000"
		assert event.payment_method == "Visa-Mastercard"

	def test_parse_paid_webhook_raises_on_invalid_signature(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"status": "paid",
			"transactionHashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			webhook_client.parse_paid_webhook(payload)

	def test_parse_failed_webhook_uses_config_vendor_key(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"errorMessage": "declined",
		}
		string_to_sign = (
			"TransactionId=12345"
			"&TransactionKey=550e8400-e29b-41d4-a716-446655440000"
			"&PaymentMethod=Visa-Mastercard"
		)
		payload["hashKey"] = self._hmac(string_to_sign)
		event = webhook_client.parse_failed_webhook(payload)

		assert event.error_message == "declined"

	def test_parse_failed_webhook_raises_on_invalid_signature(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"errorMessage": "declined",
			"hashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			webhook_client.parse_failed_webhook(payload)

	def test_parse_cancel_webhook_uses_config_vendor_key(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"referenceId": 998877,
			"paymentMethod": "Aman",
			"status": "EXPIRED",
		}
		payload["hashKey"] = self._hmac("referenceId=998877&PaymentMethod=Aman")
		event = webhook_client.parse_cancel_webhook(payload)

		assert event.reference_id == 998877

	def test_parse_cancel_webhook_raises_on_invalid_signature(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"referenceId": 998877,
			"paymentMethod": "Aman",
			"status": "EXPIRED",
			"hashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			webhook_client.parse_cancel_webhook(payload)

	def test_parse_refund_webhook_uses_config_vendor_key(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"transactionId": 12345,
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
		}
		payload["hashKey"] = self._hmac("transactionId=12345&amount=50.00&currency=EGP")
		event = webhook_client.parse_refund_webhook(payload)

		assert event.amount == "50.00"

	def test_parse_refund_webhook_raises_on_invalid_signature(
		self, webhook_client: FawaterakClient
	) -> None:
		payload = {
			"transactionId": 12345,
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
			"hashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			webhook_client.parse_refund_webhook(payload)

	def test_parse_webhook_dispatcher_invalid_signature(
		self, webhook_client: FawaterakClient
	) -> None:
		with pytest.raises(FawaterakWebhookException):
			webhook_client.parse_webhook({"hashKey": "invalid"}, WebhookType.REFUND)

	@pytest.mark.parametrize(
		"method_name",
		[
			"parse_paid_webhook",
			"parse_failed_webhook",
			"parse_cancel_webhook",
			"parse_refund_webhook",
			"parse_webhook",
		],
	)
	def test_all_webhook_methods_raise_when_vendor_key_missing(
		self, method_name: str
	) -> None:
		config = Config.resolve(
			client_id="test-client-id",
			client_secret="test-client-secret",
			base_url=BASE_URL,
		)
		http_client = HTTPClient(config.base_url, FakeTokenManager())  # ty: ignore[invalid-argument-type]
		client = FawaterakClient(config=config, http_client=http_client)

		method = getattr(client, method_name)
		with pytest.raises(FawaterakConfigException):
			if method_name == "parse_webhook":
				method({}, WebhookType.PAID)
			else:
				method({})

	def test_parse_webhook_dispatcher(self, webhook_client: FawaterakClient) -> None:
		payload = {
			"transactionId": 12345,
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
		}
		string_to_sign = "transactionId=12345&amount=50.00&currency=EGP"
		payload["hashKey"] = self._hmac(string_to_sign)

		event = webhook_client.parse_webhook(payload, WebhookType.REFUND)
		assert isinstance(event, RefundWebhookEvent)
		assert event.amount == "50.00"


class TestCreateEinvoice:
	def test_create_einvoice_returns_result(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createEinvoice",
			json={
				"status": "success",
				"data": {
					"url": "https://staging.fawaterk.com/in/abc123",
					"invoiceKey": "abc123",
					"invoiceId": 12345,
				},
			},
		)
		result = client.create_einvoice(
			currency="EGP",
			customer=Customer(
				first_name="Ahmed",
				last_name="Ali",
				customer_unique_id="user_12345",
			),
			cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
			cart_total=100.0,
		)
		assert isinstance(result, EinvoiceCreationResult)
		assert result.url == "https://staging.fawaterk.com/in/abc123"
		assert result.invoice_key == "abc123"
		assert result.invoice_id == 12345

	def test_create_einvoice_request_payload_includes_optional_fields(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createEinvoice",
			json={
				"status": "success",
				"data": {
					"url": "https://staging.fawaterk.com/in/abc123",
					"invoiceKey": "abc123",
					"invoiceId": 12345,
				},
			},
		)
		client.create_einvoice(
			currency="EGP",
			customer=Customer(
				first_name="Ahmed",
				last_name="Ali",
				email="ahmed@example.com",
				customer_unique_id="user_12345",
			),
			cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
			cart_total=100.0,
			due_date="2026-08-20",
			invoice_number="INV-001",
			pay_load={"order_id": "ORD-001"},
			redirection_urls=RedirectionUrls(
				success_url="https://example.com/success",
				fail_url="https://example.com/fail",
			),
		)
		request = requests_mock.request_history[0]
		payload = request.json()
		assert payload["currency"] == "EGP"
		assert payload["cartTotal"] == 100.0
		assert payload["cartItems"] == [
			{"name": "Order total", "price": 100.0, "quantity": 1}
		]
		assert payload["customer"]["customer_unique_id"] == "user_12345"
		assert payload["due_date"] == "2026-08-20"
		assert payload["invoice_number"] == "INV-001"
		assert payload["payLoad"] == {"order_id": "ORD-001"}
		assert payload["redirectionUrls"] == {
			"success_url": "https://example.com/success",
			"fail_url": "https://example.com/fail",
		}

	def test_create_einvoice_raises_when_customer_unique_id_missing(
		self, client: FawaterakClient
	) -> None:
		with pytest.raises(FawaterakValidationException):
			client.create_einvoice(
				currency="EGP",
				customer=Customer(first_name="Ahmed", last_name="Ali"),
				cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
				cart_total=100.0,
			)


class TestGetEinvoice:
	def test_get_einvoice_returns_invoice(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/get",
			json={
				"status": "success",
				"data": {
					"id": 12345,
					"invoice_key": "abc123",
					"vendor_id": 1,
					"vendor_username": "vendor",
					"customer_id": 99,
					"first_name": "Ahmed",
					"last_name": "Ali",
					"to_customer": 99,
					"due_date": "2026-08-20",
					"frequency": "once",
					"custom_due_date": None,
					"invoice_number": "INV-001",
					"pay_load": None,
					"type": 1,
					"invoice_type": 1,
					"tax_name": "VAT",
					"tax_amount": 14.0,
					"payment_method": "Fawry",
					"payment_method_id": 3,
					"currency": "EGP",
					"quantity": 1,
					"total": 100.0,
					"paid": 0,
					"status": 2,
					"locked": 0,
					"is_api": 1,
					"paid_at": None,
					"promocode": None,
					"discount_promocode": None,
					"created_at": "2026-08-15 10:00:00",
					"updated_at": "2026-08-15 10:00:00",
					"deleted_at": None,
					"products": [
						{
							"id": 1,
							"invoice_key": "abc123",
							"item_id": 1,
							"type": 1,
							"product_name": "Order total",
							"product_price": "100.00",
							"product_quantity": "1",
							"item_currency": "EGP",
							"total": "100.00",
							"created_at": "2026-08-15 10:00:00",
							"updated_at": "2026-08-15 10:00:00",
							"deleted_at": None,
						}
					],
					"tax_code": None,
					"tax_value": None,
					"discount_type": None,
					"discount_value": None,
					"hasHistory": False,
					"customPages": [],
					"tags": None,
					"attachment": None,
					"create_source": "API.v3.EI.IN",
				},
			},
		)
		result = client.get_einvoice(12345)
		assert isinstance(result, EInvoice)
		assert result.invoice_id == 12345
		assert result.invoice_key == "abc123"
		assert result.status == 2
		assert result.has_history is False
		assert len(result.products) == 1
		assert result.products[0].product_name == "Order total"
		assert result.products[0].product_price == "100.00"

	def test_get_einvoice_request_body(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/get",
			json={"status": "success", "data": {"id": 12345, "invoice_key": "abc123"}},
		)
		client.get_einvoice(12345)
		request = requests_mock.request_history[0]
		assert request.json() == {"invoice_id": 12345}


class TestListEinvoices:
	def test_list_einvoices_returns_paginated_results(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/index",
			json={
				"status": "success",
				"data": {
					"current_page": 1,
					"data": [
						{
							"id": 12345,
							"invoice_key": "abc123",
							"status": 2,
							"total": 100.0,
							"currency": "EGP",
						}
					],
					"from": 1,
					"last_page": 1,
					"per_page": 10,
					"to": 1,
					"total": 1,
				},
			},
		)
		result = client.list_einvoices()
		assert len(result.data) == 1
		assert result.data[0].invoice_id == 12345
		assert result.total == 1
		assert result.per_page == 10
		assert result.current_page == 1
		assert result.last_page == 1
		assert result.from_item == 1
		assert result.to_item == 1

	def test_list_einvoices_sends_filter(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/index",
			json={
				"status": "success",
				"data": {"current_page": 1, "data": [], "total": 0},
			},
		)
		client.list_einvoices(
			EinvoiceFilter(status=2, invoice_number="INV-001", customer_id=99)
		)
		request = requests_mock.request_history[0]
		assert request.json() == {
			"filter": {
				"status": 2,
				"invoice_number": "INV-001",
				"customer_id": 99,
			}
		}

	def test_list_einvoices_empty_body_when_no_filter(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/index",
			json={
				"status": "success",
				"data": {"current_page": 1, "data": [], "total": 0},
			},
		)
		client.list_einvoices()
		request = requests_mock.request_history[0]
		assert request.json() == {}


class TestUpdateEinvoice:
	def test_update_einvoice_replaces_line_items(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/update",
			json={
				"status": "success",
				"data": {
					"id": 12345,
					"invoice_key": "abc123",
					"status": 2,
					"products": [
						{
							"product_name": "Updated item",
							"product_price": "200.00",
							"product_quantity": "2",
							"total": "400.00",
						}
					],
				},
			},
		)
		result = client.update_einvoice(
			invoice_id=12345,
			customer=Customer(
				first_name="Ahmed",
				last_name="Ali",
				customer_unique_id="user_12345",
			),
			currency="EGP",
			products=[CartItem(name="Updated item", price=200.0, quantity=2)],
		)
		assert isinstance(result, EInvoice)
		assert result.invoice_id == 12345
		assert result.products[0].product_name == "Updated item"

	def test_update_einvoice_preserves_history(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/update",
			json={
				"status": "success",
				"data": {
					"id": 12345,
					"invoice_key": "abc123",
					"status": 2,
					"invoice_number": "INV-002",
					"tags": "metadata-only",
					"products": [
						{
							"product_name": "Old item",
							"product_price": "100.00",
							"product_quantity": "1",
							"total": "100.00",
						}
					],
				},
			},
		)
		result = client.update_einvoice(
			invoice_id=12345,
			customer=Customer(
				first_name="Ahmed",
				last_name="Ali",
				customer_unique_id="user_12345",
			),
			has_history=True,
			invoice_number="INV-002",
			tags="metadata-only",
		)
		assert isinstance(result, EInvoice)
		assert result.invoice_number == "INV-002"
		assert result.tags == "metadata-only"
		request = requests_mock.request_history[0]
		payload = request.json()
		assert payload["hasHistory"] is True
		assert "currency" not in payload
		assert "products" not in payload

	def test_update_einvoice_request_payload(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/update",
			json={"status": "success", "data": {"id": 12345, "invoice_key": "abc123"}},
		)
		client.update_einvoice(
			invoice_id=12345,
			customer=Customer(
				first_name="Ahmed",
				last_name="Ali",
				customer_unique_id="user_12345",
			),
			currency="EGP",
			products=[CartItem(name="Updated item", price=200.0, quantity=2)],
			due_date="2026-08-20T12:00:00Z",
			invoice_number="INV-001",
			tags="test",
		)
		request = requests_mock.request_history[0]
		payload = request.json()
		assert payload["invoice_id"] == 12345
		assert payload["customer"]["customer_unique_id"] == "user_12345"
		assert payload["currency"] == "EGP"
		assert payload["products"] == [
			{"name": "Updated item", "price": 200.0, "quantity": 2}
		]
		assert payload["due_date"] == "2026-08-20T12:00:00Z"
		assert payload["invoice_number"] == "INV-001"
		assert payload["tags"] == "test"
		assert "hasHistory" not in payload

	def test_update_einvoice_raises_when_customer_unique_id_missing(
		self, client: FawaterakClient
	) -> None:
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=12345,
				customer=Customer(first_name="Ahmed", last_name="Ali"),
				currency="EGP",
				products=[CartItem(name="Updated item", price=200.0, quantity=2)],
			)

	def test_update_einvoice_raises_when_currency_missing(
		self, client: FawaterakClient
	) -> None:
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=12345,
				customer=Customer(
					first_name="Ahmed",
					last_name="Ali",
					customer_unique_id="user_12345",
				),
				products=[CartItem(name="Updated item", price=200.0, quantity=2)],
			)

	def test_update_einvoice_raises_when_products_missing(
		self, client: FawaterakClient
	) -> None:
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=12345,
				customer=Customer(
					first_name="Ahmed",
					last_name="Ali",
					customer_unique_id="user_12345",
				),
				currency="EGP",
			)


class TestDeleteEinvoice:
	def test_delete_einvoice_returns_true(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/delete",
			json={"status": "success", "message": "invoice deleted"},
		)
		result = client.delete_einvoice(12345)
		assert result is True

	def test_delete_einvoice_request_body(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/delete",
			json={"status": "success", "message": "invoice deleted"},
		)
		client.delete_einvoice(12345)
		request = requests_mock.request_history[0]
		assert request.json() == {"invoice_id": 12345}

	def test_delete_einvoice_api_error_raises(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/delete",
			json={"status": "error", "message": "Invoice cannot be deleted"},
			status_code=422,
		)
		with pytest.raises(FawaterakValidationException):
			client.delete_einvoice(12345)


@pytest.mark.integration
class TestEinvoiceStagingIntegration:
	"""Live e-invoice tests against Fawaterak staging. Run with real credentials."""

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
		return FawaterakClient(config=Config.resolve())

	@pytest.fixture
	def integration_customer(self) -> Customer:
		return Customer(
			first_name="Integration",
			last_name="Test",
			email="integration@example.com",
			customer_unique_id=f"ei-integration-{uuid.uuid4().hex[:8]}",
		)

	@pytest.fixture
	def created_invoice(
		self, staging_client: FawaterakClient, integration_customer: Customer
	) -> EinvoiceCreationResult:
		result = staging_client.create_einvoice(
			currency="EGP",
			customer=integration_customer,
			cart_items=[CartItem(name="Test order", price=100.0, quantity=1)],
			cart_total=100.0,
		)
		assert result.invoice_id
		assert result.invoice_key
		assert result.url.startswith("http")
		return result

	def test_create_einvoice(self, created_invoice: EinvoiceCreationResult) -> None:
		assert created_invoice.invoice_id > 0
		assert created_invoice.invoice_key
		assert created_invoice.url.startswith("http")

	def test_get_einvoice(
		self,
		staging_client: FawaterakClient,
		created_invoice: EinvoiceCreationResult,
	) -> None:
		fetched = staging_client.get_einvoice(created_invoice.invoice_id)
		assert fetched.invoice_id == created_invoice.invoice_id
		assert fetched.invoice_key == created_invoice.invoice_key

	def test_list_einvoices(
		self,
		staging_client: FawaterakClient,
		created_invoice: EinvoiceCreationResult,
	) -> None:
		page = staging_client.list_einvoices()
		assert any(item.invoice_id == created_invoice.invoice_id for item in page.data)

	def test_update_einvoice_replace_line_items(
		self,
		staging_client: FawaterakClient,
		created_invoice: EinvoiceCreationResult,
		integration_customer: Customer,
	) -> None:
		updated = staging_client.update_einvoice(
			invoice_id=created_invoice.invoice_id,
			customer=integration_customer,
			currency="EGP",
			products=[CartItem(name="Updated item", price=200.0, quantity=2)],
		)
		assert updated.invoice_id == created_invoice.invoice_id
		assert any(p.product_name == "Updated item" for p in updated.products)

	def test_update_einvoice_preserves_history(
		self,
		staging_client: FawaterakClient,
		created_invoice: EinvoiceCreationResult,
		integration_customer: Customer,
	) -> None:
		updated = staging_client.update_einvoice(
			invoice_id=created_invoice.invoice_id,
			customer=integration_customer,
			has_history=True,
			tags="integration-test",
		)
		assert updated.invoice_id == created_invoice.invoice_id
		assert updated.tags == "integration-test"

	def test_delete_einvoice(
		self,
		staging_client: FawaterakClient,
		created_invoice: EinvoiceCreationResult,
	) -> None:
		result = staging_client.delete_einvoice(created_invoice.invoice_id)
		assert result is True


@pytest.mark.integration
class TestStagingIntegration:
	"""Live smoke tests against Fawaterak staging. Run with real credentials."""

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
