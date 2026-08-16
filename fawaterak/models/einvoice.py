"""E-invoice models: creation results, invoice details, and list filters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .common import _omit_none


@dataclass(frozen=True)
class EinvoiceCreationResult:
	"""
	Result of successful E-Invoice creation.

	maps to https://staging.fawaterk.com/documentation#models/CreateEinvoiceSuccess
	"""

	url: str
	invoice_key: str
	invoice_id: int

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> EinvoiceCreationResult:
		return cls(
			url=data.get("url", ""),
			invoice_key=data.get("invoiceKey", ""),
			invoice_id=int(data.get("invoiceId", 0)),
		)


@dataclass(frozen=True)
class EinvoiceProduct:
	"""
	One line item on an e-invoice.

	The spec does not schematize the invoice detail object, so this mirrors
	the shape observed on staging. Price/quantity/total come back as strings.
	"""

	id: int | None
	invoice_key: str | None
	item_id: int | None
	type: int | None
	product_name: str
	product_price: str
	product_quantity: str
	item_currency: str | None
	total: str
	created_at: str | None
	updated_at: str | None
	deleted_at: str | None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> EinvoiceProduct:
		return cls(
			id=int(data["id"]) if data.get("id") is not None else None,
			invoice_key=data.get("invoice_key"),
			item_id=(int(data["item_id"]) if data.get("item_id") is not None else None),
			type=int(data["type"]) if data.get("type") is not None else None,
			product_name=data.get("product_name", ""),
			product_price=data.get("product_price", ""),
			product_quantity=data.get("product_quantity", ""),
			item_currency=data.get("item_currency"),
			total=data.get("total", ""),
			created_at=data.get("created_at"),
			updated_at=data.get("updated_at"),
			deleted_at=data.get("deleted_at"),
		)


@dataclass(frozen=True)
class EInvoice:
	"""
	Full e-invoice detail returned by get/update and list items.

	The documentation leaves this shape unknown ("Full e-invoice detail object"),
	so fields mirror what was observed on staging and parsing is defensive:
	missing or unexpected keys degrade to defaults instead of raising.

	`invoice_id` maps from the payload's `id` key; the API identifies invoices
	by `invoice_id` in requests.
	"""

	invoice_id: int
	invoice_key: str
	vendor_id: int | None
	vendor_username: str | None
	customer_id: int | None
	first_name: str | None
	last_name: str | None
	to_customer: int | None
	due_date: str | None
	frequency: str | None
	custom_due_date: str | None
	invoice_number: str | None
	pay_load: Any
	type: int | None
	invoice_type: int | None
	tax_name: Any
	tax_amount: float | None
	payment_method: str | None
	payment_method_id: int | None
	currency: str | None
	quantity: int | None
	total: float
	paid: int
	status: int
	locked: int
	is_api: int
	paid_at: str | None
	promocode: str | None
	discount_promocode: str | None
	created_at: str | None
	updated_at: str | None
	deleted_at: str | None
	products: list[EinvoiceProduct] = field(default_factory=list)
	tax_code: str | None = None
	tax_value: str | None = None
	discount_type: str | None = None
	discount_value: str | None = None
	has_history: bool = False
	custom_pages: list[Any] = field(default_factory=list)
	tags: str | None = None
	attachment: str | None = None
	create_source: str | None = None

	@classmethod
	def from_dict(cls, data: dict[str, Any]) -> EInvoice:
		return cls(
			invoice_id=int(data.get("id")),  # ty: ignore[invalid-argument-type]
			invoice_key=data.get("invoice_key", ""),
			vendor_id=(
				int(data["vendor_id"]) if data.get("vendor_id") is not None else None
			),
			vendor_username=data.get("vendor_username"),
			customer_id=(
				int(data["customer_id"])
				if data.get("customer_id") is not None
				else None
			),
			first_name=data.get("first_name"),
			last_name=data.get("last_name"),
			to_customer=(
				int(data["to_customer"])
				if data.get("to_customer") is not None
				else None
			),
			due_date=data.get("due_date"),
			frequency=data.get("frequency"),
			custom_due_date=data.get("custom_due_date"),
			invoice_number=data.get("invoice_number"),
			pay_load=data.get("pay_load"),
			type=int(data["type"]) if data.get("type") is not None else None,
			invoice_type=(
				int(data["invoice_type"])
				if data.get("invoice_type") is not None
				else None
			),
			tax_name=data.get("tax_name"),
			tax_amount=(
				float(data["tax_amount"])
				if data.get("tax_amount") is not None
				else None
			),
			payment_method=data.get("payment_method"),
			payment_method_id=(
				int(data["payment_method_id"])
				if data.get("payment_method_id") is not None
				else None
			),
			currency=data.get("currency"),
			quantity=(
				int(data["quantity"]) if data.get("quantity") is not None else None
			),
			total=float(data.get("total", 0)),
			paid=int(data.get("paid", 0)),
			status=int(data.get("status", 0)),
			locked=int(data.get("locked", 0)),
			is_api=int(data.get("is_api", 0)),
			paid_at=data.get("paid_at"),
			promocode=data.get("promocode"),
			discount_promocode=data.get("discount_promocode"),
			created_at=data.get("created_at"),
			updated_at=data.get("updated_at"),
			deleted_at=data.get("deleted_at"),
			products=[
				EinvoiceProduct.from_dict(item) for item in data.get("products", [])
			],
			tax_code=data.get("tax_code"),
			tax_value=data.get("tax_value"),
			discount_type=data.get("discount_type"),
			discount_value=data.get("discount_value"),
			has_history=bool(data.get("hasHistory", False)),
			custom_pages=data.get("customPages", []),
			tags=data.get("tags"),
			attachment=data.get("attachment"),
			create_source=data.get("create_source"),
		)


@dataclass(frozen=True)
class EinvoiceFilter:
	"""
	Optional filter for listing e-invoices.

	maps to https://staging.fawaterk.com/documentation#models/ListEinvoicesRequest
	"""

	status: int | None = None
	invoice_number: str | None = None
	customer_id: int | None = None

	def to_dict(self) -> dict[str, Any]:
		return _omit_none(asdict(self))
