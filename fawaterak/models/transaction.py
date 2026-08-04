"""Transaction-related models: results, payment-data unions, and export items."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class PaymentResult:
	"""
	Base class for direct-payment provider response shapes.

	All children class amount to One Of https://app.fawaterk.com/documentation#models/TransactionPaymentData
	"""


@dataclass(frozen=True)
class CardPaymentResult(PaymentResult):
	"""
	Card / redirect method response containing a 3DS or provider URL.

	maps to partial https://app.fawaterk.com/documentation#models/TransactionPaymentData
	"""

	redirect_to: str


@dataclass(frozen=True)
class ReferenceCodeResult(PaymentResult):
	"""
	Fawry / Aman / Masary response containing a reference code and expiry.

	maps to partial https://app.fawaterk.com/documentation#models/TransactionPaymentData
	"""

	reference_number: str
	expire_date: str
	expiration_time: str


@dataclass(frozen=True)
class MobileWalletResult(PaymentResult):
	"""
	Meeza-style wallet response containing an RTP reference and QR payload.

	maps to partial https://app.fawaterk.com/documentation#models/TransactionPaymentData
	"""

	system_reference: str
	iso_qr: str


@dataclass(frozen=True)
class UnknownPaymentResult(PaymentResult):
	"""Fallback for payment_data shapes not yet explicitly modeled."""

	raw: dict[str, Any]


def parse_payment_data(payment_data: dict[str, Any]) -> PaymentResult:
	"""Inspect response keys and return the appropriate PaymentResult subclass."""
	if "redirectTo" in payment_data:
		return CardPaymentResult(redirect_to=payment_data["redirectTo"])
	if "referenceNumber" in payment_data:
		return ReferenceCodeResult(
			reference_number=payment_data["referenceNumber"],
			expire_date=payment_data["expireDate"],
			expiration_time=payment_data["expirationTime"],
		)
	if "systemReference" in payment_data:
		return MobileWalletResult(
			system_reference=payment_data["systemReference"],
			iso_qr=payment_data["isoQr"],
		)
	return UnknownPaymentResult(raw=payment_data)


@dataclass(frozen=True)
class TransactionResult:
	"""
	Base fields present in every createTransaction response.

	shared fields in https://app.fawaterk.com/documentation#models/TransactionLinkData
	"""

	intent_key: str
	expires_in: int


@dataclass(frozen=True)
class HostedCheckoutResult(TransactionResult):
	"""
	Response when no payment_method_id was supplied (link mode).

	maps to https://app.fawaterk.com/documentation#tag/api-integration/POST/api/v3/createTransaction
	in specific case of Hosted Checkout Response.

	short_url & short_code might be missing, as they are mentioned in the documentation not in documnetation models.
	"""

	url: str
	short_url: str | None = None
	short_code: str | None = None


@dataclass(frozen=True)
class DirectPaymentResult(TransactionResult):
	"""
	Response when payment_method_id was supplied (direct-dispatch mode).

	maps to https://app.fawaterk.com/documentation#tag/api-integration/POST/api/v3/createTransaction
	in specific case of Direct Payment Response.
	"""

	payment_data: PaymentResult


@dataclass(frozen=True)
class PaymentMethodHistoryItem:
	"""
	One entry in a transaction’s payment-history list.
	
	maps to https://app.fawaterk.com/documentation#models/PaymentMethodHistoryItem
	"""

	method_name: str
	method_logo: str | None
	amount: str
	currency: str
	status: str
	reference: str | None
	date: str

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> PaymentMethodHistoryItem:
		method = data.get("method", {})
		return cls(
			method_name=method.get("name", ""),
			method_logo=method.get("logo"),
			amount=data.get("amount", ""),
			currency=data.get("currency", ""),
			status=data.get("status", ""),
			reference=data.get("reference"),
			date=data.get("date", ""),
		)


@dataclass(frozen=True)
class TransactionData:
	"""
	Full transaction details from POST /api/v3/getTransactionData.
	
	maps to https://app.fawaterk.com/documentation#models/TransactionDetail
	"""

	intent_key: str
	transaction_id: int
	customer_email: str | None
	commission: float | None
	transaction_created_at: str | None
	paid: int
	paid_at: str | None
	status_text: str
	total: float
	currency: str
	payment_method: str
	pay_load: Any
	due_date: str | None
	transaction_link: str
	transaction_history: list[PaymentMethodHistoryItem] = field(default_factory=list)

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> TransactionData:
		history = [
			PaymentMethodHistoryItem.from_dict(item)
			for item in data.get("transaction_history", [])
		]
		return cls(
			intent_key=data["intent_key"],
			transaction_id=int(data.get("transaction_id", 0)),
			customer_email=data.get("customer_email"),
			commission=(
				float(data["commission"])
				if data.get("commission") is not None
				else None
			),
			transaction_created_at=data.get("transaction_created_at"),
			paid=int(data.get("paid", 0)),
			paid_at=data.get("paid_at"),
			status_text=data.get("status_text", ""),
			total=float(data.get("total", 0)),
			currency=data.get("currency", ""),
			payment_method=data.get("payment_method", ""),
			pay_load=data.get("pay_load"),
			due_date=data.get("due_date"),
			transaction_link=data.get("transaction_link", ""),
			transaction_history=history,
		)


@dataclass(frozen=True)
class TransactionExportItem:
	"""
	One row in a paginated transaction export.
	
	maps to https://app.fawaterk.com/documentation#models/TransactionExportItem
	"""

	transaction_id: int
	intent_key: str
	invoice_id: int | None
	customer_email: str | None
	transaction_created_at: str
	status_text: str
	total: float
	currency: str
	pay_load: Any
	payment_method: str
	transaction_transactions: list[dict[str, Any]]
	original_amount_egp: float | None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> TransactionExportItem:
		return cls(
			transaction_id=int(data["transaction_id"]),
			intent_key=data["intent_key"],
			invoice_id=(
				int(data["invoice_id"]) if data.get("invoice_id") is not None else None
			),
			customer_email=data.get("customer_email"),
			transaction_created_at=data.get("transaction_created_at", ""),
			status_text=data.get("status_text", ""),
			total=float(data.get("total", 0)),
			currency=data.get("currency", ""),
			pay_load=data.get("pay_load"),
			payment_method=data.get("payment_method", ""),
			transaction_transactions=data.get("transaction_transactions", []),
			original_amount_egp=(
				float(data["original_amount_egp"])
				if data.get("original_amount_egp") is not None
				else None
			),
		)


@dataclass(frozen=True)
class Page(Generic[T]):
	"""
	Paginated response metadata.
	
	maps to https://app.fawaterk.com/documentation#models/PaginationMeta
	"""

	data: list[T]
	total: int
	per_page: int
	current_page: int
	last_page: int
	from_item: int | None
	to_item: int | None
