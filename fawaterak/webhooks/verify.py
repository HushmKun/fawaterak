"""
HMAC verification for Fawaterak webhook payloads.

The verification functions are intentionally framework-independent:
you pass the parsed webhook body as a dict and the vendor API key.
Signature extraction and string-to-sign construction are handled internally.
"""

from __future__ import annotations

import hashlib
import hmac
from enum import Enum
from typing import Any


class WebhookType(str, Enum):
	"""
	Known Fawaterak webhook types.

	Will be migrated to StrEnum when 3.9 & 3.10 support is dropped.
	"""

	PAID = "paid"
	FAILED = "failed"
	CANCEL = "cancel"
	REFUND = "refund"
	TOKENIZATION = "tokenization"


def _hmac_hex(key: str, message: str) -> str:
	"""Return the HMAC-SHA256 hex digest of ``message`` using ``key``."""
	return hmac.new(
		key.encode("utf-8"),
		message.encode("utf-8"),
		hashlib.sha256,
	).hexdigest()


def _extract_signature(payload: dict[str, Any], *keys: str) -> str | None:
	"""
	Return the first non-empty signature value found under the given keys.
	This was made because of the mess of having both Trx-style and legacy
	in the same class.
	"""
	for key in keys:
		value = payload.get(key)
		if value:
			return str(value)
	return None


def _verify(
	payload: dict[str, Any],
	vendor_api_key: str,
	string_to_sign: str | None,
	*signature_keys: str,
) -> bool:
	"""Generic helper: build signature, compare, and return True on match."""
	if string_to_sign is None:
		return False

	expected_signature = _extract_signature(payload, *signature_keys)
	if expected_signature is None:
		return False

	computed_signature = _hmac_hex(vendor_api_key, string_to_sign)
	return hmac.compare_digest(computed_signature, expected_signature)


def _build_paid_string(payload: dict[str, Any]) -> str | None:
	"""
	String to sign for paid/pending webhooks.

	Handling both Trx-style and legacy keys.
	"""
	transaction_id = payload.get("transaction_id")
	transaction_key = payload.get("transaction_key")
	payment_method = payload.get("payment_method")

	if transaction_id is not None and transaction_key and payment_method:
		return (
			f"TransactionId={transaction_id}"
			f"&TransactionKey={transaction_key}"
			f"&PaymentMethod={payment_method}"
		)

	invoice_id = payload.get("invoice_id")
	invoice_key = payload.get("invoice_key")
	if invoice_id is not None and invoice_key and payment_method:
		return (
			f"InvoiceId={invoice_id}"
			f"&InvoiceKey={invoice_key}"
			f"&PaymentMethod={payment_method}"
		)

	return None


def _build_failed_string(payload: dict[str, Any]) -> str | None:
	"""String to sign for failed-payment webhooks."""
	return _build_paid_string(payload)


def _build_cancel_string(payload: dict[str, Any]) -> str | None:
	"""String to sign for cancel/expired webhooks."""
	reference_id = payload.get("referenceId")
	payment_method = payload.get("paymentMethod")

	if reference_id is None or not payment_method:
		return None

	return f"referenceId={reference_id}&PaymentMethod={payment_method}"


def _build_refund_string(payload: dict[str, Any]) -> str | None:
	"""String to sign for refund webhooks."""
	transaction_id = payload.get("transactionId")
	amount = payload.get("amount")
	currency = payload.get("currency")

	if transaction_id is None or amount is None or currency is None:
		return None

	return f"transactionId={transaction_id}&amount={amount}&currency={currency}"


def verify_paid_webhook(payload: dict[str, Any], vendor_api_key: str) -> bool:
	"""Verify the HMAC signature of a paid/pending webhook payload."""
	return _verify(
		payload,
		vendor_api_key,
		_build_paid_string(payload),
		"transactionHashKey",
		"hashKey",
	)


def verify_failed_webhook(payload: dict[str, Any], vendor_api_key: str) -> bool:
	"""Verify the HMAC signature of a failed-payment webhook payload."""
	return _verify(
		payload,
		vendor_api_key,
		_build_failed_string(payload),
		"hashKey",
	)


def verify_cancel_webhook(payload: dict[str, Any], vendor_api_key: str) -> bool:
	"""Verify the HMAC signature of a cancel/expired webhook payload."""
	return _verify(
		payload,
		vendor_api_key,
		_build_cancel_string(payload),
		"hashKey",
	)


def verify_refund_webhook(payload: dict[str, Any], vendor_api_key: str) -> bool:
	"""
	Verify the HMAC signature of a refund webhook payload.
	"""
	return _verify(
		payload,
		vendor_api_key,
		_build_refund_string(payload),
		"hashKey",
	)


def verify_tokenization_webhook(payload: dict[str, Any], vendor_api_key: str) -> bool:
	"""
	Verify the HMAC signature of a tokenization webhook payload.

	Raises NotImplementedError:
		tokenization webhook verification is planned for later.
	"""
	msg = "Tokenization webhook verification is planned for later."
	raise NotImplementedError(msg)


def verify_webhook(
	payload: dict[str, Any],
	vendor_api_key: str,
	webhook_type: WebhookType,
) -> bool:
	"""
	Dispatch to the correct verifier for the given webhook type.

	I have deliberated a lot regarding this functions:
			- Is it necessary? no
			- Would I use it later? can't decide
			- Will I remove it? also no
	The trick is in the future I will probably need some form of this
	function or not, but I will leave it here for now.
	"""
	verifiers = {
		WebhookType.PAID: verify_paid_webhook,
		WebhookType.FAILED: verify_failed_webhook,
		WebhookType.CANCEL: verify_cancel_webhook,
		WebhookType.REFUND: verify_refund_webhook,
		WebhookType.TOKENIZATION: verify_tokenization_webhook,
	}
	verifier = verifiers[webhook_type]
	return verifier(payload, vendor_api_key)
