"""Typed dataclasses for Fawaterak webhook payloads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models.transaction import FinancialBreakdown


@dataclass(frozen=True)
class PaidWebhookEvent:
	"""
	Paid or pending payment webhook payload.

	Supports both API v3 Trx-style fields (`transaction_key`, `transaction_id`,
	`status`) and legacy invoice-style fields (`invoice_key`, `invoice_id`,
	`invoice_status`).
	Both field sets are optional because a given payload carries one or the other.
	`financial_breakdown` is only present on paid webhooks after settlement.
	Webhook body encoding (json, x-www-form-urlencoded), to force json add `_json`
	to the end of the webhook url.

	Maps to https://staging.fawaterk.com/documentation#models/PaymentWebhookPayload
	"""

	transaction_key: str | None
	transaction_id: int | None
	invoice_key: str | None
	invoice_id: int | None
	status: str | None
	invoice_status: str | None
	payment_method: str
	pay_load: str | None
	paid_amount: str | None
	paid_currency: str | None
	paid_at: str | None
	reference_number: str | None
	customer_data: dict[str, Any] | None
	fees: str | None = None
	card_discount_amount: str | None = None
	discount_bank_code: str | None = None
	payment_token: str | None = None
	financial_breakdown: FinancialBreakdown | None = None
	transaction_hash_key: str | None = None
	hash_key: str | None = None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> PaidWebhookEvent:
		return cls(
			transaction_key=data.get("transaction_key"),
			transaction_id=(
				int(data["transaction_id"])
				if data.get("transaction_id") is not None
				else None
			),
			invoice_key=data.get("invoice_key"),
			invoice_id=(
				int(data["invoice_id"]) if data.get("invoice_id") is not None else None
			),
			status=data.get("status"),
			invoice_status=data.get("invoice_status"),
			payment_method=data.get("payment_method", ""),
			pay_load=data.get("pay_load"),
			paid_amount=data.get("paidAmount"),
			paid_currency=data.get("paidCurrency"),
			paid_at=data.get("paidAt"),
			reference_number=data.get("referenceNumber"),
			customer_data=data.get("customerData"),
			fees=data.get("fees"),
			card_discount_amount=data.get("cardDiscountAmount"),
			discount_bank_code=data.get("discountBankCode"),
			payment_token=data.get("paymentToken"),
			financial_breakdown=FinancialBreakdown.from_optional(
				data.get("financial_breakdown")
			),
			transaction_hash_key=data.get("transactionHashKey"),
			hash_key=data.get("hashKey"),
		)


@dataclass(frozen=True)
class FailedWebhookEvent:
	"""
	Failed payment webhook payload.

	Like `PaidWebhookEvent`, this normalizes both Trx-style and legacy invoice
	references into one flat result type.
	Webhook body encoding (json, x-www-form-urlencoded), to force json add `_json`
	to the end of the webhook url.

	Maps to https://staging.fawaterk.com/documentation#models/FailedPaymentWebhookPayload
	"""

	transaction_key: str | None
	transaction_id: int | None
	invoice_key: str | None
	invoice_id: int | None
	payment_method: str | None
	pay_load: str | None
	amount: str | None
	paid_currency: str | None
	error_message: str | None
	response: str | None
	hash_key: str | None = None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> FailedWebhookEvent:
		return cls(
			transaction_key=data.get("transaction_key"),
			transaction_id=(
				int(data["transaction_id"])
				if data.get("transaction_id") is not None
				else None
			),
			invoice_key=data.get("invoice_key"),
			invoice_id=(
				int(data["invoice_id"]) if data.get("invoice_id") is not None else None
			),
			payment_method=data.get("payment_method"),
			pay_load=data.get("pay_load"),
			amount=data.get("amount"),
			paid_currency=data.get("paidCurrency"),
			error_message=data.get("errorMessage"),
			response=data.get("response"),
			hash_key=data.get("hashKey"),
		)


@dataclass(frozen=True)
class CancelWebhookEvent:
	"""
	Cancel or expired reference webhook payload.

	`transaction_id`/`transaction_key` are the parent transaction identifiers when
	present; `reference_id` and `payment_method` are used for HMAC verification.
	Webhook body encoding (json)

	Maps to https://staging.fawaterk.com/documentation#models/CancelReferenceWebhookPayload
	"""

	reference_id: int
	status: str
	payment_method: str
	pay_load: str | None
	transaction_id: int | None
	transaction_key: str | None
	hash_key: str | None = None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> CancelWebhookEvent:
		return cls(
			reference_id=int(data["referenceId"]),
			status=data.get("status", ""),
			payment_method=data.get("paymentMethod", ""),
			pay_load=data.get("pay_load"),
			transaction_id=(
				int(data["transactionId"])
				if data.get("transactionId") is not None
				else None
			),
			transaction_key=data.get("transactionKey"),
			hash_key=data.get("hashKey"),
		)


@dataclass(frozen=True)
class RefundWebhookEvent:
	"""
	Refund approved webhook payload.

	The signature covers `transactionId`, `amount`, and `currency`.
	Webhook body encoding (json)

	Maps to https://staging.fawaterk.com/documentation#models/RefundWebhookPayload
	"""

	transaction_id: int
	amount: str
	currency: str
	status: int
	reason: str | None
	approved_at: str | None
	hash_key: str | None = None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> RefundWebhookEvent:
		return cls(
			transaction_id=int(data["transactionId"]),
			amount=data.get("amount", ""),
			currency=data.get("currency", ""),
			status=int(data.get("status", 0)),
			reason=data.get("reason"),
			approved_at=data.get("approvedAt"),
			hash_key=data.get("hashKey"),
		)


@dataclass(frozen=True)
class TokenizationWebhookEvent:
	"""
	Saved-card token created webhook payload (legacy v2 tokenization).

	This is a placeholder for now. I am not yet implementing this.

	Maps to (They didn't make an equivalent model)
	https://staging.fawaterk.com/documentation#tag/tokenization-and-recurring:~:text=Created%20token%20webhook
	"""

	customer_unique_id: str
	customer_card: str
	customer_card_token: str
	card_brand: str
	card_token_unique_id: str
	hash_key: str

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> TokenizationWebhookEvent:
		return cls(
			customer_unique_id=data.get("customerUniqueId", ""),
			customer_card=data.get("customerCard", ""),
			customer_card_token=data.get("customerCardToken", ""),
			card_brand=data.get("cardBrand", ""),
			card_token_unique_id=data.get("cardTokenUniqueId", ""),
			hash_key=data.get("hashKey", ""),
		)
