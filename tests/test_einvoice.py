"""Unit tests for the E-Invoicing surface of FawaterakClient."""

from __future__ import annotations

import pytest
import requests_mock

from fawaterak._http import HTTPClient
from fawaterak.client import FawaterakClient
from fawaterak.config import Config
from fawaterak.exceptions import FawaterakValidationException
from fawaterak.models.common import CartItem, Customer, RedirectionUrls
from fawaterak.models.einvoice import EInvoice, EinvoiceCreationResult, EinvoiceFilter

BASE_URL = "https://api.example.com"


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


EINVOICE_DETAIL = {
	"id": 1105654,
	"invoice_key": "ocE7zQl4J7hm93U",
	"vendor_id": 1303,
	"vendor_username": "testvendor",
	"customer_id": 73340,
	"first_name": "Hussein",
	"last_name": "Mukhtar",
	"to_customer": 1,
	"due_date": "2026-08-14 00:00:00",
	"frequency": "once",
	"custom_due_date": "default",
	"invoice_number": "",
	"pay_load": None,
	"type": 0,
	"invoice_type": 1,
	"tax_name": 1,
	"tax_amount": None,
	"payment_method": None,
	"payment_method_id": None,
	"currency": "EGP",
	"quantity": 1,
	"total": 150,
	"paid": 0,
	"status": 2,
	"locked": 0,
	"is_api": 1,
	"paid_at": None,
	"promocode": None,
	"discount_promocode": None,
	"created_at": "2026-08-12",
	"updated_at": "2026-08-12",
	"deleted_at": None,
	"products": [
		{
			"id": 146770,
			"invoice_key": "ocE7zQl4J7hm93U",
			"item_id": None,
			"type": 2,
			"product_name": "Widget",
			"product_price": "150.00",
			"product_quantity": "1",
			"item_currency": None,
			"total": "150.00",
			"created_at": "2026-08-12T20:18:36.000000Z",
			"updated_at": "2026-08-12T20:18:36.000000Z",
			"deleted_at": None,
		}
	],
	"tax_code": "",
	"tax_value": "",
	"discount_type": "",
	"discount_value": "",
	"hasHistory": True,
	"customPages": [],
	"tags": None,
	"attachment": "",
	"create_source": "API.v3.EI.IN",
}


class TestCreateEinvoice:
	def test_returns_creation_result(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createEinvoice",
			json={
				"status": "success",
				"data": {
					"url": "https://staging.fawaterk.com/in/ocE7zQl4J7hm93U",
					"invoiceKey": "ocE7zQl4J7hm93U",
					"invoiceId": 1105654,
				},
			},
		)
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		result = client.create_einvoice(
			currency="EGP",
			customer=customer,
			cart_items=[CartItem(name="Widget", price=150.0, quantity=1)],
			cart_total=150.0,
		)
		assert isinstance(result, EinvoiceCreationResult)
		assert result.invoice_id == 1105654
		assert result.invoice_key == "ocE7zQl4J7hm93U"
		assert result.url.startswith("https://")

	def test_request_payload_includes_optional_fields(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/createEinvoice",
			json={
				"status": "success",
				"data": {
					"url": "https://staging.fawaterk.com/in/ocE7zQl4J7hm93U",
					"invoiceKey": "ocE7zQl4J7hm93U",
					"invoiceId": 1105654,
				},
			},
		)
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		redirection_urls = RedirectionUrls(
			success_url="https://example.com/success",
			fail_url="https://example.com/fail",
		)
		client.create_einvoice(
			currency="EGP",
			customer=customer,
			cart_items=[CartItem(name="Widget", price=150.0, quantity=1)],
			cart_total=150.0,
			due_date="2026-08-14",
			invoice_number="INV-1",
			pay_load={"order_id": "ORD-1001"},
			redirection_urls=redirection_urls,
		)
		payload = requests_mock.request_history[0].json()
		assert payload["due_date"] == "2026-08-14"
		assert payload["invoice_number"] == "INV-1"
		assert payload["payLoad"] == {"order_id": "ORD-1001"}
		assert (
			payload["redirectionUrls"]["success_url"] == "https://example.com/success"
		)

	def test_missing_customer_unique_id_raises(self, client: FawaterakClient) -> None:
		customer = Customer(first_name="Hussein", last_name="Mukhtar")
		with pytest.raises(FawaterakValidationException):
			client.create_einvoice(
				currency="EGP",
				customer=customer,
				cart_items=[CartItem(name="Widget", price=150.0, quantity=1)],
				cart_total=150.0,
			)


class TestGetEinvoice:
	def test_returns_parsed_invoice(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/get",
			json={"status": "success", "data": EINVOICE_DETAIL},
		)
		invoice = client.get_einvoice(1105654)
		assert isinstance(invoice, EInvoice)
		assert invoice.invoice_id == 1105654
		assert invoice.invoice_key == "ocE7zQl4J7hm93U"
		assert invoice.status == 2
		assert invoice.has_history is True
		assert invoice.create_source == "API.v3.EI.IN"
		assert len(invoice.products) == 1
		assert invoice.products[0].product_name == "Widget"
		assert invoice.products[0].product_price == "150.00"

	def test_request_body_contains_invoice_id(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/get",
			json={"status": "success", "data": EINVOICE_DETAIL},
		)
		client.get_einvoice(1105654)
		assert requests_mock.request_history[0].json() == {"invoice_id": 1105654}


class TestListEinvoices:
	def test_no_filter_sends_empty_body(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		paginator = {
			"current_page": 1,
			"data": [EINVOICE_DETAIL],
			"from": 1,
			"last_page": 1,
			"per_page": 10,
			"to": 1,
			"total": 1,
		}
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/index",
			json={"status": "success", "data": paginator},
		)
		page = client.list_einvoices()
		assert len(page.data) == 1
		assert page.total == 1
		assert page.per_page == 10
		assert page.last_page == 1
		assert page.data[0].invoice_id == 1105654
		assert requests_mock.request_history[0].json() == {}

	def test_filter_is_wrapped_under_filter_key(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		paginator = {
			"current_page": 1,
			"data": [],
			"from": None,
			"last_page": 1,
			"per_page": 10,
			"to": None,
			"total": 0,
		}
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/index",
			json={"status": "success", "data": paginator},
		)
		page = client.list_einvoices(EinvoiceFilter(status=2))
		assert page.total == 0
		assert requests_mock.request_history[0].json() == {"filter": {"status": 2}}


class TestUpdateEinvoice:
	def test_full_update_payload(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/update",
			json={"status": "success", "data": EINVOICE_DETAIL},
		)
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		result = client.update_einvoice(
			invoice_id=1105654,
			customer=customer,
			has_history=False,
			currency="EGP",
			products=[CartItem(name="Widget", price=150.0, quantity=1)],
			invoice_number="INV-1",
			tags="vip",
			due_date="2026-08-14T00:00:00",
		)
		assert isinstance(result, EInvoice)
		assert result.invoice_id == 1105654
		payload = requests_mock.request_history[0].json()
		assert payload["invoice_id"] == 1105654
		assert payload["customer"]["customer_unique_id"] == "cust_1"
		assert payload["currency"] == "EGP"
		assert payload["products"] == [
			{"name": "Widget", "price": 150.0, "quantity": 1}
		]
		assert "hasHistory" not in payload
		assert payload["invoice_number"] == "INV-1"
		assert payload["tags"] == "vip"

	def test_update_with_has_history_skips_currency_products(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/update",
			json={"status": "success", "data": EINVOICE_DETAIL},
		)
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		client.update_einvoice(
			invoice_id=1105654,
			customer=customer,
			has_history=True,
			invoice_number="INV-1",
		)
		payload = requests_mock.request_history[0].json()
		assert payload.get("currency") is None
		assert payload.get("products") is None
		assert payload["hasHistory"] is True

	def test_update_without_history_requires_currency_and_products(
		self, client: FawaterakClient
	) -> None:
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=1105654,
				customer=customer,
				has_history=False,
			)

	def test_update_missing_customer_unique_id_raises(
		self, client: FawaterakClient
	) -> None:
		customer = Customer(first_name="Hussein", last_name="Mukhtar")
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=1105654,
				customer=customer,
				has_history=True,
			)


class TestDeleteEinvoice:
	def test_returns_true_on_success(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/delete",
			json={"status": "success", "message": "invoice deleted"},
		)
		assert client.delete_einvoice(1105654) is True

	def test_request_body_contains_invoice_id(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/delete",
			json={"status": "success", "message": "invoice deleted"},
		)
		client.delete_einvoice(1105654)
		assert requests_mock.request_history[0].json() == {"invoice_id": 1105654}


class TestUpdateEinvoiceAdditional:
	def test_update_requires_both_currency_and_products_when_no_history(
		self, client: FawaterakClient
	) -> None:
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=1105654,
				customer=customer,
				has_history=False,
				currency="EGP",
			)
		with pytest.raises(FawaterakValidationException):
			client.update_einvoice(
				invoice_id=1105654,
				customer=customer,
				has_history=False,
				products=[CartItem(name="Widget", price=150.0, quantity=1)],
			)

	def test_update_result_parses_staging_detail(
		self, client: FawaterakClient, requests_mock: requests_mock.Mocker
	) -> None:
		requests_mock.post(
			f"{BASE_URL}/api/v3/invoice/update",
			json={"status": "success", "data": EINVOICE_DETAIL},
		)
		customer = Customer(
			first_name="Hussein",
			last_name="Mukhtar",
			customer_unique_id="cust_1",
		)
		result = client.update_einvoice(
			invoice_id=1105654,
			customer=customer,
			has_history=True,
		)
		assert result.invoice_id == 1105654
		assert result.status == 2
		assert result.has_history is True
		assert result.create_source == "API.v3.EI.IN"
		assert len(result.products) == 1
		assert result.products[0].product_price == "150.00"


class TestEinvoiceModels:
	def test_einvoice_product_parses_with_missing_fields(
		self,
	) -> None:
		from fawaterak.models.einvoice import EinvoiceProduct

		product = EinvoiceProduct.from_dict({"product_name": "Widget"})
		assert product.product_name == "Widget"
		assert product.product_price == ""
		assert product.id is None
		assert product.item_id is None
		assert product.total == ""
		assert product.created_at is None

	def test_einvoice_parses_with_minimal_keys(self) -> None:
		from fawaterak.models.einvoice import EInvoice

		invoice = EInvoice.from_dict({"id": 42})
		assert invoice.invoice_id == 42
		assert invoice.invoice_key == ""
		assert invoice.total == 0.0
		assert invoice.paid == 0
		assert invoice.status == 0
		assert invoice.products == []
		assert invoice.custom_pages == []
		assert invoice.tags is None
		assert invoice.has_history is False

	def test_einvoice_creation_result_parses_defensively(self) -> None:
		from fawaterak.models.einvoice import EinvoiceCreationResult

		result = EinvoiceCreationResult.from_dict({})
		assert isinstance(result, EinvoiceCreationResult)
		assert result.url == ""
		assert result.invoice_key == ""
		assert result.invoice_id == 0
