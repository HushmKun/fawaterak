"""Unit tests for common and payment-method models."""

from __future__ import annotations

from fawaterak.models.common import (
	CartItem,
	Customer,
	DiscountData,
	RedirectionUrls,
	TaxData,
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
