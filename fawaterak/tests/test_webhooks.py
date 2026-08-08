"""Unit tests for Fawaterak webhook verification and parsing."""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import pytest

from fawaterak.exceptions import FawaterakWebhookException
from fawaterak.webhooks import (
	CancelWebhookEvent,
	FailedWebhookEvent,
	PaidWebhookEvent,
	RefundWebhookEvent,
	WebhookType,
	parse_cancel_webhook,
	parse_failed_webhook,
	parse_paid_webhook,
	parse_refund_webhook,
	parse_webhook,
	verify_cancel_webhook,
	verify_failed_webhook,
	verify_paid_webhook,
	verify_refund_webhook,
	verify_tokenization_webhook,
	verify_webhook,
)

VENDOR_API_KEY = "test-vendor-api-key"


def _hmac(message: str) -> str:
	return hmac.new(
		VENDOR_API_KEY.encode("utf-8"),
		message.encode("utf-8"),
		hashlib.sha256,
	).hexdigest()


class TestVerifyPaidWebhook:
	def _payload(self, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
		payload: dict[str, Any] = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"status": "paid",
			"paidAmount": "150.00",
			"paidCurrency": "EGP",
		}
		string_to_sign = (
			"TransactionId=12345"
			"&TransactionKey=550e8400-e29b-41d4-a716-446655440000"
			"&PaymentMethod=Visa-Mastercard"
		)
		payload["transactionHashKey"] = _hmac(string_to_sign)
		if overrides:
			payload.update(overrides)
		return payload

	def test_valid_transaction_hash_key_returns_true(self) -> None:
		assert verify_paid_webhook(self._payload(), VENDOR_API_KEY) is True

	def test_valid_legacy_hash_key_returns_true(self) -> None:
		payload = self._payload()
		del payload["transactionHashKey"]
		string_to_sign = (
			"TransactionId=12345"
			"&TransactionKey=550e8400-e29b-41d4-a716-446655440000"
			"&PaymentMethod=Visa-Mastercard"
		)
		payload["hashKey"] = _hmac(string_to_sign)
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is True

	def test_invalid_signature_returns_false(self) -> None:
		payload = self._payload()
		payload["transactionHashKey"] = "invalid"
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_signature_returns_false(self) -> None:
		payload = self._payload()
		del payload["transactionHashKey"]
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is False

	def test_legacy_invoice_fields(self) -> None:
		payload = {
			"invoice_key": "11111111-1111-1111-1111-111111111111",
			"invoice_id": 987,
			"payment_method": "Visa-Mastercard",
			"invoice_status": "paid",
		}
		string_to_sign = (
			"InvoiceId=987"
			"&InvoiceKey=11111111-1111-1111-1111-111111111111"
			"&PaymentMethod=Visa-Mastercard"
		)
		payload["hashKey"] = _hmac(string_to_sign)
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is True

	def test_missing_transaction_and_invoice_fields_returns_false(self) -> None:
		payload = {"payment_method": "Visa-Mastercard"}
		payload["transactionHashKey"] = _hmac("anything")
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_transaction_hash_key_and_hash_key(self) -> None:
		payload = self._payload()
		del payload["transactionHashKey"]
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is False

	def test_transaction_id_zero(self) -> None:
		payload = self._payload({"transaction_id": 0})
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is False

	def test_empty_payment_method(self) -> None:
		payload = self._payload({"payment_method": ""})
		assert verify_paid_webhook(payload, VENDOR_API_KEY) is False


class TestVerifyFailedWebhook:
	def _payload(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
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
		payload["hashKey"] = _hmac(string_to_sign)
		return payload

	def test_valid_signature_returns_true(self) -> None:
		assert verify_failed_webhook(self._payload(), VENDOR_API_KEY) is True

	def test_invalid_signature_returns_false(self) -> None:
		payload = self._payload()
		payload["hashKey"] = "invalid"
		assert verify_failed_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_hash_key(self) -> None:
		payload = self._payload()
		del payload["hashKey"]
		assert verify_failed_webhook(payload, VENDOR_API_KEY) is False


class TestVerifyCancelWebhook:
	def _payload(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
			"referenceId": 998877,
			"paymentMethod": "Aman",
			"status": "EXPIRED",
		}
		string_to_sign = "referenceId=998877&PaymentMethod=Aman"
		payload["hashKey"] = _hmac(string_to_sign)
		return payload

	def test_valid_signature_returns_true(self) -> None:
		assert verify_cancel_webhook(self._payload(), VENDOR_API_KEY) is True

	def test_invalid_signature_returns_false(self) -> None:
		payload = self._payload()
		payload["hashKey"] = "invalid"
		assert verify_cancel_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_reference_or_payment_method_returns_false(self) -> None:
		payload = {"paymentMethod": "Aman", "hashKey": _hmac("anything")}
		assert verify_cancel_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_hash_key(self) -> None:
		payload = self._payload()
		del payload["hashKey"]
		assert verify_cancel_webhook(payload, VENDOR_API_KEY) is False


class TestVerifyRefundWebhook:
	def _payload(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
			"transactionId": 12345,
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
		}
		string_to_sign = "transactionId=12345&amount=50.00&currency=EGP"
		payload["hashKey"] = _hmac(string_to_sign)
		return payload

	def test_valid_signature_returns_true(self) -> None:
		assert verify_refund_webhook(self._payload(), VENDOR_API_KEY) is True

	def test_invalid_signature_returns_false(self) -> None:
		payload = self._payload()
		payload["hashKey"] = "invalid"
		assert verify_refund_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_hash_key(self) -> None:
		payload = self._payload()
		del payload["hashKey"]
		assert verify_refund_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_amount(self) -> None:
		payload = self._payload()
		del payload["amount"]
		assert verify_refund_webhook(payload, VENDOR_API_KEY) is False

	def test_missing_currency(self) -> None:
		payload = self._payload()
		del payload["currency"]
		assert verify_refund_webhook(payload, VENDOR_API_KEY) is False


class TestVerifyWebhookDispatcher:
	def test_dispatches_by_type(self) -> None:
		payload = {
			"referenceId": 111,
			"paymentMethod": "Masary",
			"status": "CANCELED",
			"hashKey": _hmac("referenceId=111&PaymentMethod=Masary"),
		}
		assert verify_webhook(payload, VENDOR_API_KEY, WebhookType.CANCEL) is True

	def test_tokenization_stub_raises_not_implemented(self) -> None:
		with pytest.raises(NotImplementedError):
			verify_tokenization_webhook({}, VENDOR_API_KEY)

	def test_dispatcher_raises_for_tokenization(self) -> None:
		with pytest.raises(NotImplementedError):
			verify_webhook({}, VENDOR_API_KEY, WebhookType.TOKENIZATION)

	def test_invalid_signature(self) -> None:
		payload = {
			"referenceId": 111,
			"paymentMethod": "Masary",
			"status": "CANCELED",
			"hashKey": "invalid",
		}
		assert verify_webhook(payload, VENDOR_API_KEY, WebhookType.CANCEL) is False

	def test_unknown_type(self) -> None:
		with pytest.raises(FawaterakWebhookException):
			verify_webhook({}, VENDOR_API_KEY, "unknown")  # ty: ignore[invalid-argument-type]


class TestParsePaidWebhook:
	def _payload(self) -> dict[str, Any]:
		payload: dict[str, Any] = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"status": "paid",
			"paidAmount": "150.00",
			"paidCurrency": "EGP",
			"paidAt": "2026-06-01 14:30:00",
			"customerData": {
				"customer_unique_id": "cust-42",
				"customer_first_name": "Ahmed",
				"customer_last_name": "Ali",
			},
		}
		string_to_sign = (
			"TransactionId=12345"
			"&TransactionKey=550e8400-e29b-41d4-a716-446655440000"
			"&PaymentMethod=Visa-Mastercard"
		)
		payload["transactionHashKey"] = _hmac(string_to_sign)
		return payload

	def test_parses_valid_payload(self) -> None:
		event = parse_paid_webhook(self._payload(), VENDOR_API_KEY)
		assert isinstance(event, PaidWebhookEvent)
		assert event.transaction_id == 12345
		assert event.status == "paid"
		assert event.payment_method == "Visa-Mastercard"
		assert event.customer_data is not None

	def test_raises_on_invalid_signature(self) -> None:
		payload = self._payload()
		payload["transactionHashKey"] = "invalid"
		with pytest.raises(FawaterakWebhookException):
			parse_paid_webhook(payload, VENDOR_API_KEY)

	def test_missing_signature(self) -> None:
		payload = self._payload()
		del payload["transactionHashKey"]
		with pytest.raises(FawaterakWebhookException):
			parse_paid_webhook(payload, VENDOR_API_KEY)

	def test_form_encoded_payload_as_dict(self) -> None:
		"""Form bodies are the framework's responsibility; a flat dict works."""
		payload = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Fawry",
			"status": "pending",
		}
		string_to_sign = (
			"TransactionId=12345"
			"&TransactionKey=550e8400-e29b-41d4-a716-446655440000"
			"&PaymentMethod=Fawry"
		)
		payload["transactionHashKey"] = _hmac(string_to_sign)
		event = parse_paid_webhook(payload, VENDOR_API_KEY)
		assert event.status == "pending"


class TestParseFailedWebhook:
	def test_parses_valid_payload(self) -> None:
		payload: dict[str, Any] = {
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
		payload["hashKey"] = _hmac(string_to_sign)
		event = parse_failed_webhook(payload, VENDOR_API_KEY)
		assert isinstance(event, FailedWebhookEvent)
		assert event.error_message == "declined"

	def test_raises_on_invalid_signature(self) -> None:
		payload: dict[str, Any] = {
			"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
			"transaction_id": 12345,
			"payment_method": "Visa-Mastercard",
			"hashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			parse_failed_webhook(payload, VENDOR_API_KEY)


class TestParseCancelWebhook:
	def test_parses_valid_payload(self) -> None:
		payload: dict[str, Any] = {
			"referenceId": 998877,
			"paymentMethod": "Aman",
			"status": "EXPIRED",
			"transactionId": 12345,
			"transactionKey": "550e8400-e29b-41d4-a716-446655440000",
		}
		string_to_sign = "referenceId=998877&PaymentMethod=Aman"
		payload["hashKey"] = _hmac(string_to_sign)
		event = parse_cancel_webhook(payload, VENDOR_API_KEY)
		assert isinstance(event, CancelWebhookEvent)
		assert event.reference_id == 998877
		assert event.transaction_id == 12345

	def test_raises_on_invalid_signature(self) -> None:
		payload: dict[str, Any] = {
			"referenceId": 998877,
			"paymentMethod": "Aman",
			"status": "EXPIRED",
			"hashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			parse_cancel_webhook(payload, VENDOR_API_KEY)

	def test_missing_reference_id_keyerror(self) -> None:
		payload: dict[str, Any] = {
			"paymentMethod": "Aman",
			"status": "EXPIRED",
			"hashKey": _hmac("anything"),
		}
		with pytest.raises(FawaterakWebhookException):
			parse_cancel_webhook(payload, VENDOR_API_KEY)


class TestParseRefundWebhook:
	def test_parses_valid_payload(self) -> None:
		payload: dict[str, Any] = {
			"transactionId": 12345,
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
			"reason": "Customer requested refund",
			"approvedAt": "2026-06-02 10:15:00",
		}
		string_to_sign = "transactionId=12345&amount=50.00&currency=EGP"
		payload["hashKey"] = _hmac(string_to_sign)
		event = parse_refund_webhook(payload, VENDOR_API_KEY)
		assert isinstance(event, RefundWebhookEvent)
		assert event.amount == "50.00"
		assert event.reason == "Customer requested refund"

	def test_raises_on_invalid_signature(self) -> None:
		payload: dict[str, Any] = {
			"transactionId": 12345,
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
			"hashKey": "invalid",
		}
		with pytest.raises(FawaterakWebhookException):
			parse_refund_webhook(payload, VENDOR_API_KEY)

	def test_missing_transaction_id_keyerror(self) -> None:
		payload: dict[str, Any] = {
			"amount": "50.00",
			"currency": "EGP",
			"status": 1,
			"hashKey": _hmac("anything"),
		}
		with pytest.raises(FawaterakWebhookException):
			parse_refund_webhook(payload, VENDOR_API_KEY)


class TestParseWebhookDispatcher:
	def test_parses_by_type(self) -> None:
		payload: dict[str, Any] = {
			"transactionId": 12345,
			"amount": "10.00",
			"currency": "EGP",
			"status": 1,
		}
		string_to_sign = "transactionId=12345&amount=10.00&currency=EGP"
		payload["hashKey"] = _hmac(string_to_sign)
		event = parse_webhook(payload, VENDOR_API_KEY, WebhookType.REFUND)
		assert isinstance(event, RefundWebhookEvent)

	def test_tokenization_stub_raises_not_implemented(self) -> None:
		with pytest.raises(NotImplementedError):
			parse_webhook({}, VENDOR_API_KEY, WebhookType.TOKENIZATION)

	@pytest.mark.parametrize(
		"webhook_type",
		[
			WebhookType.PAID,
			WebhookType.FAILED,
			WebhookType.CANCEL,
			WebhookType.REFUND,
		],
	)
	def test_invalid_signature_per_type(self, webhook_type: WebhookType) -> None:
		with pytest.raises(FawaterakWebhookException):
			parse_webhook({"hashKey": "invalid"}, VENDOR_API_KEY, webhook_type)


class TestEventFromDictEdgeCases:
	def test_paid_event_string_transaction_id(self) -> None:
		event = PaidWebhookEvent.from_dict(
			{
				"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
				"transaction_id": "12345",
				"payment_method": "Visa-Mastercard",
				"status": "paid",
			}
		)
		assert event.transaction_id == 12345

	def test_paid_event_none_invoice_status(self) -> None:
		event = PaidWebhookEvent.from_dict(
			{
				"transaction_key": "550e8400-e29b-41d4-a716-446655440000",
				"transaction_id": 12345,
				"payment_method": "Visa-Mastercard",
				"status": "paid",
				"invoice_status": None,
			}
		)
		assert event.invoice_status is None

	def test_failed_event_invoice_fields(self) -> None:
		event = FailedWebhookEvent.from_dict(
			{
				"invoice_key": "11111111-1111-1111-1111-111111111111",
				"invoice_id": 987,
				"payment_method": "Visa-Mastercard",
			}
		)
		assert event.invoice_id == 987
		assert event.invoice_key == "11111111-1111-1111-1111-111111111111"

	def test_cancel_event_missing_optional_transaction(self) -> None:
		event = CancelWebhookEvent.from_dict(
			{
				"referenceId": 998877,
				"paymentMethod": "Aman",
				"status": "EXPIRED",
			}
		)
		assert event.reference_id == 998877
		assert event.transaction_id is None
		assert event.transaction_key is None

	def test_refund_event_missing_optional_reason_approved_at(self) -> None:
		event = RefundWebhookEvent.from_dict(
			{
				"transactionId": 12345,
				"amount": "50.00",
				"currency": "EGP",
				"status": 1,
			}
		)
		assert event.reason is None
		assert event.approved_at is None
