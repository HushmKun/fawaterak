"""Unit tests for common and payment-method models."""

from __future__ import annotations

from fawaterak.models.common import (
	CartItem,
	Customer,
	DiscountData,
	RedirectionUrls,
	TaxData,
)
from fawaterak.models.einvoice import (
	EInvoice,
	EinvoiceCreationResult,
	EinvoiceFilter,
	EinvoiceProduct,
)
from fawaterak.models.payment_method import PaymentMethod


class TestCustomer:
	def test_to_dict_omits_none_values(self) -> None:
		customer = Customer(
			first_name="Ahmed",
			last_name="Ali",
			email="ahmed@example.com",
		)
		result = customer.to_dict()
		assert result == {
			"first_name": "Ahmed",
			"last_name": "Ali",
			"email": "ahmed@example.com",
		}
		assert "phone" not in result
		assert "address" not in result


class TestCartItem:
	def test_to_dict(self) -> None:
		item = CartItem(name="Order total", price=100.0, quantity=1)
		assert item.to_dict() == {
			"name": "Order total",
			"price": 100.0,
			"quantity": 1,
		}


class TestRedirectionUrls:
	def test_to_dict_omits_none_values(self) -> None:
		urls = RedirectionUrls(
			success_url="https://example.com/success",
			fail_url="https://example.com/fail",
		)
		result = urls.to_dict()
		assert result == {
			"success_url": "https://example.com/success",
			"fail_url": "https://example.com/fail",
		}
		assert "pending_url" not in result


class TestTaxData:
	def test_to_dict(self) -> None:
		tax = TaxData(title="VAT", value=14.0)
		assert tax.to_dict() == {"title": "VAT", "value": 14.0}


class TestDiscountData:
	def test_pcg_to_dict(self) -> None:
		discount = DiscountData(type="pcg", value=10.0)
		assert discount.to_dict() == {"type": "pcg", "value": 10.0}

	def test_literal_to_dict(self) -> None:
		discount = DiscountData(type="literal", value=10.0)
		assert discount.to_dict() == {"type": "literal", "value": 10.0}


class TestPaymentMethod:
	def test_from_dict(self) -> None:
		data = {
			"payment_method_id": 3,
			"name_en": "Fawry",
			"name_ar": "فوري",
			"redirect": "false",
			"logo": "https://example.com/fawry.png",
			"commission_on_customer": 2,
			"integration_status": 1,
		}
		method = PaymentMethod.from_dict(data)
		assert method.payment_method_id == 3
		assert method.name_en == "Fawry"
		assert method.redirect is False
		assert method.logo == "https://example.com/fawry.png"
		assert method.commission_on_customer == 2

	def test_from_dict_handles_missing_logo_and_integration_status(self) -> None:
		data = {
			"payment_method_id": 2,
			"name_en": "Visa-Mastercard",
			"name_ar": "فيزا -ماستر كارد",
			"redirect": "true",
			"commission_on_customer": 1,
		}
		method = PaymentMethod.from_dict(data)
		assert method.logo is None
		assert method.integration_status is None
		assert method.redirect is True


class TestEinvoiceCreationResult:
	def test_from_dict(self) -> None:
		data = {
			"url": "https://staging.fawaterk.com/in/abc123",
			"invoiceKey": "abc123",
			"invoiceId": 12345,
		}
		result = EinvoiceCreationResult.from_dict(data)
		assert result.url == "https://staging.fawaterk.com/in/abc123"
		assert result.invoice_key == "abc123"
		assert result.invoice_id == 12345

	def test_from_dict_handles_missing_values(self) -> None:
		result = EinvoiceCreationResult.from_dict({})
		assert result.url == ""
		assert result.invoice_key == ""
		assert result.invoice_id == 0


class TestEinvoiceProduct:
	def test_from_dict(self) -> None:
		data = {
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
		product = EinvoiceProduct.from_dict(data)
		assert product.id == 1
		assert product.invoice_key == "abc123"
		assert product.product_name == "Order total"
		assert product.product_price == "100.00"
		assert product.total == "100.00"

	def test_from_dict_handles_missing_optional_fields(self) -> None:
		data = {
			"product_name": "Order total",
			"product_price": "100.00",
			"product_quantity": "1",
			"total": "100.00",
		}
		product = EinvoiceProduct.from_dict(data)
		assert product.id is None
		assert product.invoice_key is None
		assert product.item_id is None
		assert product.type is None
		assert product.item_currency is None
		assert product.created_at is None


class TestEInvoice:
	def _invoice_data(self) -> dict:
		return {
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
			"hasHistory": True,
			"customPages": [],
			"tags": None,
			"attachment": None,
			"create_source": "API.v3.EI.IN",
		}

	def test_from_dict(self) -> None:
		invoice = EInvoice.from_dict(self._invoice_data())
		assert invoice.invoice_id == 12345
		assert invoice.invoice_key == "abc123"
		assert invoice.vendor_id == 1
		assert invoice.customer_id == 99
		assert invoice.first_name == "Ahmed"
		assert invoice.total == 100.0
		assert invoice.status == 2
		assert invoice.has_history is True
		assert len(invoice.products) == 1
		assert invoice.products[0].product_name == "Order total"
		assert invoice.custom_pages == []
		assert invoice.create_source == "API.v3.EI.IN"

	def test_from_dict_handles_missing_optional_fields(self) -> None:
		data = {
			"id": 12345,
			"invoice_key": "abc123",
			"total": 100.0,
			"paid": 0,
			"status": 2,
			"locked": 0,
			"is_api": 0,
		}
		invoice = EInvoice.from_dict(data)
		assert invoice.invoice_id == 12345
		assert invoice.vendor_id is None
		assert invoice.customer_id is None
		assert invoice.products == []
		assert invoice.has_history is False
		assert invoice.custom_pages == []

	def test_from_dict_maps_has_history(self) -> None:
		data = self._invoice_data()
		data["hasHistory"] = False
		invoice = EInvoice.from_dict(data)
		assert invoice.has_history is False

	def test_from_dict_maps_custom_pages(self) -> None:
		data = self._invoice_data()
		data["customPages"] = [{"key": "value"}]
		invoice = EInvoice.from_dict(data)
		assert invoice.custom_pages == [{"key": "value"}]


class TestEinvoiceFilter:
	def test_to_dict_omits_none_values(self) -> None:
		filter_ = EinvoiceFilter(status=2)
		assert filter_.to_dict() == {"status": 2}

	def test_to_dict_includes_all_fields(self) -> None:
		filter_ = EinvoiceFilter(status=2, invoice_number="INV-001", customer_id=99)
		assert filter_.to_dict() == {
			"status": 2,
			"invoice_number": "INV-001",
			"customer_id": 99,
		}
