"""Payment method model returned by GET /api/v3/getTrPaymentmethods."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class PaymentMethod:
	"""
	One integration-enabled payment method for the vendor account.

	maps to https://app.fawaterk.com/documentation#models/VendorPaymentMethodItem
	"""

	payment_method_id: int
	name_en: str
	name_ar: str
	redirect: bool
	logo: str | None
	commission_on_customer: Literal[1, 2]
	integration_status: int | None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> PaymentMethod:
		return cls(
			payment_method_id=int(data["payment_method_id"]),
			name_en=data["name_en"],
			name_ar=data["name_ar"],
			redirect=data["redirect"] == "true",
			logo=data.get("logo"),
			commission_on_customer=int(data["commission_on_customer"]),  # ty: ignore[invalid-argument-type]
			integration_status=(
				int(data["integration_status"])
				if data.get("integration_status") is not None
				else None
			),
		)
