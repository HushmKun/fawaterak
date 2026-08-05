"""Shared request-building models for Fawaterak API calls."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


def _omit_none(data: dict[str, Any]) -> dict[str, Any]:
	"""Remove keys whose value is None; keep falsy values like 0 or False."""
	return {k: v for k, v in data.items() if v is not None}


@dataclass
class Customer:
	"""
	Customer details attached to a transaction or e-invoice.

	maps to https://app.fawaterk.com/documentation#models/Customer
	"""

	first_name: str
	last_name: str
	email: str | None = None
	phone: str | None = None
	address: str | None = None
	customer_number: str | None = None
	customer_unique_id: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return _omit_none(asdict(self))


@dataclass
class CartItem:
	"""
	One line item in a transaction cart.

	maps to https://app.fawaterk.com/documentation#models/CartItem
	"""

	name: str
	price: float
	quantity: int

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


@dataclass
class RedirectionUrls:
	"""
	Customer redirect URLs and optional per-transaction webhook override.

	maps to https://app.fawaterk.com/documentation#models/RedirectionUrls
	"""

	success_url: str
	fail_url: str
	pending_url: str | None = None
	back_url: str | None = None
	webhook_url: str | None = None

	def to_dict(self) -> dict[str, Any]:
		return _omit_none(asdict(self))


@dataclass
class TaxData:
	"""
	Tax applied at transaction creation time.

	maps to https://app.fawaterk.com/documentation#models/TaxData
	"""

	title: str
	value: float

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)


@dataclass
class DiscountData:
	"""
	Discount applied at transaction creation time.

	maps to https://app.fawaterk.com/documentation#models/DiscountData
	"""

	type: Literal["pcg", "literal"]  # Un-enforceable
	value: float

	def to_dict(self) -> dict[str, Any]:
		return asdict(self)
