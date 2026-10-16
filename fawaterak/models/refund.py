"""Refund models: refund types, creation results, and refund request records."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any


class RefundType(str, enum.Enum):
	"""
	The `refund_type` code the refund API expects (as a string).

	- `INVOICE` — e-invoice / invoice record; `refund_id` is the invoice id.
	- `PAYMENT_LINK_TRANSACTION` — payment link transaction; `refund_id` is the
	  payment-request transaction id.
	- `COLLECTION_LINK_TRANSACTION` — collection link transaction.
	- `INTEGRATION_TRANSACTION` — transaction created through the API; the id
	  is the transaction id visible via `get_transaction`.
	"""

	INVOICE = "0"
	PAYMENT_LINK_TRANSACTION = "1"
	COLLECTION_LINK_TRANSACTION = "2"
	INTEGRATION_TRANSACTION = "3"


@dataclass(frozen=True)
class RefundCreationResult:
	"""Result of a successful refund request submission."""

	status: str
	message: str

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> RefundCreationResult:
		return cls(
			status=data.get("status", ""),
			message=data.get("message", ""),
		)


@dataclass(frozen=True)
class RefundRequest:
	"""
	One refund request record, as returned by list or details.

	The refunds list and the single-refund details endpoint return the same
	core record; only the list carries `refundable_type`, `refundable_id` and
	`can_delete`, so those degrade to `None` when parsed from a details
	response. Amounts come back as strings on the wire and are parsed to
	`float`.
	"""

	id: int
	refundable_amount: float
	status: str
	reason: str
	created_at: str | None
	refundable_type: str | None = None
	refundable_id: int | None = None
	can_delete: bool | None = None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> RefundRequest:
		return cls(
			id=int(data["id"]),
			refundable_amount=float(data.get("refundable_amount", 0)),
			status=data.get("status", ""),
			reason=data.get("reason", ""),
			created_at=data.get("created_at"),
			refundable_type=data.get("refundable_type"),
			refundable_id=(
				int(data["refundable_id"])
				if data.get("refundable_id") is not None
				else None
			),
			can_delete=data.get("can_delete"),
		)
