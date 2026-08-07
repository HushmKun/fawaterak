"""Typed webhook parsers that verify HMAC signatures before parsing."""

from __future__ import annotations

from typing import Any

from ..exceptions import FawaterakWebhookException
from .events import (
	CancelWebhookEvent,
	FailedWebhookEvent,
	PaidWebhookEvent,
	RefundWebhookEvent,
	TokenizationWebhookEvent,
)
from .verify import (
	WebhookType,
	verify_cancel_webhook,
	verify_failed_webhook,
	verify_paid_webhook,
	verify_refund_webhook,
	verify_tokenization_webhook,
)

WebhooksParseResult = (
	PaidWebhookEvent
	| FailedWebhookEvent
	| CancelWebhookEvent
	| RefundWebhookEvent
	| TokenizationWebhookEvent
)


def parse_paid_webhook(
	payload: dict[str, Any], vendor_api_key: str
) -> PaidWebhookEvent:
	"""Verify and parse a paid/pending webhook payload."""
	if not verify_paid_webhook(payload, vendor_api_key):
		raise FawaterakWebhookException("paid webhook signature verification failed")
	return PaidWebhookEvent.from_dict(payload)


def parse_failed_webhook(
	payload: dict[str, Any], vendor_api_key: str
) -> FailedWebhookEvent:
	"""Verify and parse a failed-payment webhook payload."""
	if not verify_failed_webhook(payload, vendor_api_key):
		raise FawaterakWebhookException("failed webhook signature verification failed")
	return FailedWebhookEvent.from_dict(payload)


def parse_cancel_webhook(
	payload: dict[str, Any], vendor_api_key: str
) -> CancelWebhookEvent:
	"""Verify and parse a cancel/expired webhook payload."""
	if not verify_cancel_webhook(payload, vendor_api_key):
		raise FawaterakWebhookException("cancel webhook signature verification failed")
	return CancelWebhookEvent.from_dict(payload)


def parse_refund_webhook(
	payload: dict[str, Any], vendor_api_key: str
) -> RefundWebhookEvent:
	"""Verify and parse a refund webhook payload."""
	if not verify_refund_webhook(payload, vendor_api_key):
		raise FawaterakWebhookException("refund webhook signature verification failed")
	return RefundWebhookEvent.from_dict(payload)


def parse_tokenization_webhook(
	payload: dict[str, Any], vendor_api_key: str
) -> TokenizationWebhookEvent:
	"""Verify and parse a tokenization webhook payload.

	Raises:
		NotImplementedError: tokenization webhook parsing is planned for Phase 8.
	"""
	if not verify_tokenization_webhook(payload, vendor_api_key):
		raise FawaterakWebhookException(
			"tokenization webhook signature verification failed"
		)
	return TokenizationWebhookEvent.from_dict(payload)


def parse_webhook(
	payload: dict[str, Any],
	vendor_api_key: str,
	webhook_type: WebhookType,
) -> WebhooksParseResult:
	"""
	Verify and parse a webhook payload of the given type.
	"""
	parsers = {
		WebhookType.PAID: parse_paid_webhook,
		WebhookType.FAILED: parse_failed_webhook,
		WebhookType.CANCEL: parse_cancel_webhook,
		WebhookType.REFUND: parse_refund_webhook,
		WebhookType.TOKENIZATION: parse_tokenization_webhook,
	}
	parser = parsers[webhook_type]
	return parser(payload, vendor_api_key)
