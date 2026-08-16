"""Public synchronous client for the Fawaterak API v3."""

from __future__ import annotations

from datetime import date
from functools import cache
from typing import Any

from ._http import HTTPClient
from .config import Config
from .exceptions import FawaterakConfigException, FawaterakValidationException
from .models.common import (
	CartItem,
	Customer,
	DiscountData,
	RedirectionUrls,
	TaxData,
)
from .models.einvoice import (
	EInvoice,
	EinvoiceCreationResult,
	EinvoiceFilter,
)
from .models.payment_method import PaymentMethod
from .models.transaction import (
	DirectPaymentResult,
	HostedCheckoutResult,
	Page,
	TransactionData,
	TransactionExportItem,
	parse_payment_data,
)
from .webhooks import (
	CancelWebhookEvent,
	FailedWebhookEvent,
	PaidWebhookEvent,
	RefundWebhookEvent,
	WebhooksParseResult,
	WebhookType,
	parse_cancel_webhook,
	parse_failed_webhook,
	parse_paid_webhook,
	parse_refund_webhook,
	parse_webhook,
)


class FawaterakClient:
	"""High-level client for Fawaterak API v3 transaction endpoints."""

	def __init__(
		self,
		config: Config | None = None,
		http_client: HTTPClient | None = None,
	) -> None:
		self._config = config or Config.resolve()
		if http_client is not None:
			self._http = http_client
		else:
			from .auth import TokenManager

			token_manager = TokenManager(
				self._config.client_id,
				self._config.client_secret,
				self._config.base_url,
			)
			self._http = HTTPClient(
				self._config.base_url,
				token_manager,
				timeout=self._config.timeout,
			)

	@cache  # noqa: B019
	def get_payment_methods(self) -> list[PaymentMethod]:
		"""Return all integration-enabled payment methods for this vendor."""
		response = self._http.request("GET", "/api/v3/getTrPaymentmethods")
		data = response.get("data", [])
		return [PaymentMethod.from_dict(item) for item in data]

	def _require_vendor_api_key(self) -> str:
		if not self._config.vendor_api_key:
			raise FawaterakConfigException(
				"vendor_api_key is required for webhook verification. "
				"Pass it to Config.resolve() or set FAWATERAK_VENDOR_API_KEY."
			)
		return self._config.vendor_api_key

	def create_transaction(
		self,
		*,
		currency: str,
		customer: Customer,
		cart_items: list[CartItem],
		cart_total: float,
		payment_method_id: int | None = None,
		mobile_wallet_number: str | None = None,
		save_customer: bool = False,
		pay_load: dict[str, Any] | None = None,
		redirection_urls: RedirectionUrls | None = None,
		send_email: bool = False,
		send_sms: bool = False,
		due_date: str | None = None,
		tr_number: str | None = None,
		redirect_option: bool = False,
		auth_and_capture: int | None = None,
		tax_data: TaxData | None = None,
		discount_data: DiscountData | None = None,
		list_style: str = "h",
		lang: str = "en",
	) -> HostedCheckoutResult | DirectPaymentResult:
		"""Create a transaction in hosted-checkout or direct-payment mode."""
		payload: dict[str, Any] = {
			"currency": currency,
			"cartTotal": cart_total,
			"customer": customer.to_dict(),
			"cartItems": [item.to_dict() for item in cart_items],
			"save_customer": save_customer,
			"sendEmail": send_email,
			"sendSMS": send_sms,
			"redirectOption": redirect_option,
			"list_style": list_style,
			"lang": lang,
		}

		if payment_method_id is not None:
			payload["payment_method_id"] = payment_method_id
		if mobile_wallet_number is not None:
			payload["mobileWalletNumber"] = mobile_wallet_number
		if pay_load is not None:
			payload["pay_load"] = pay_load
		if redirection_urls is not None:
			payload["redirectionUrls"] = redirection_urls.to_dict()
		if due_date is not None:
			payload["due_date"] = due_date
		if tr_number is not None:
			payload["tr_number"] = tr_number
		if auth_and_capture is not None:
			payload["authAndCapture"] = auth_and_capture
		if tax_data is not None:
			payload["taxData"] = tax_data.to_dict()
		if discount_data is not None:
			payload["discountData"] = discount_data.to_dict()

		response = self._http.request("POST", "/api/v3/createTransaction", json=payload)
		data = response.get("data", {})

		if "url" in data:
			return HostedCheckoutResult(
				intent_key=data["intent_key"],
				expires_in=int(data["expires_in"]),
				url=data["url"],
				short_url=data.get("short_url"),
				short_code=data.get("short_code"),
			)

		return DirectPaymentResult(
			intent_key=data["intent_key"],
			expires_in=int(data["expires_in"]),
			payment_data=parse_payment_data(data.get("payment_data", {})),
		)

	def get_transaction(self, intent_key: str) -> TransactionData:
		"""Fetch one transaction by its intent key."""
		response = self._http.request(
			"POST",
			"/api/v3/getTransactionData",
			json={"intent_key": intent_key},
		)
		return TransactionData.from_dict(response.get("data", {}))

	def list_transactions(
		self,
		*,
		start_date: date | str,
		end_date: date | str,
		page: int = 1,
		per_page: int = 15,
		pay_load: str | None = None,
	) -> Page[TransactionExportItem]:
		"""Return a paginated export of persisted transactions."""
		start = start_date.isoformat() if isinstance(start_date, date) else start_date
		end = end_date.isoformat() if isinstance(end_date, date) else end_date

		params: dict[str, Any] = {
			"start_date": start,
			"end_date": end,
			"page": page,
			"per_page": per_page,
		}
		if pay_load is not None:
			params["pay_load"] = pay_load

		response = self._http.request(
			"GET",
			"/api/v3/getTransactionsData",
			params=params,
		)

		items = [
			TransactionExportItem.from_dict(item) for item in response.get("data", [])
		]
		pagination = response.get("pagination", {})

		return Page(
			data=items,
			total=int(pagination.get("total", 0)),
			per_page=int(pagination.get("per_page", 0)),
			current_page=int(pagination.get("current_page", 1)),
			last_page=int(pagination.get("last_page", 1)),
			from_item=pagination.get("from"),
			to_item=pagination.get("to"),
		)

	def parse_paid_webhook(self, payload: dict[str, Any]) -> PaidWebhookEvent:
		"""Verify and parse a paid/pending webhook payload."""
		return parse_paid_webhook(payload, self._require_vendor_api_key())

	def parse_failed_webhook(self, payload: dict[str, Any]) -> FailedWebhookEvent:
		"""Verify and parse a failed-payment webhook payload."""
		return parse_failed_webhook(payload, self._require_vendor_api_key())

	def parse_cancel_webhook(self, payload: dict[str, Any]) -> CancelWebhookEvent:
		"""Verify and parse a cancel/expired webhook payload."""
		return parse_cancel_webhook(payload, self._require_vendor_api_key())

	def parse_refund_webhook(self, payload: dict[str, Any]) -> RefundWebhookEvent:
		"""Verify and parse a refund webhook payload."""
		return parse_refund_webhook(payload, self._require_vendor_api_key())

	def parse_webhook(
		self,
		payload: dict[str, Any],
		webhook_type: WebhookType,
	) -> WebhooksParseResult:
		"""Verify and parse a webhook payload of the given type."""
		return parse_webhook(payload, self._require_vendor_api_key(), webhook_type)

	def create_einvoice(
		self,
		*,
		currency: str,
		customer: Customer,
		cart_items: list[CartItem],
		cart_total: float,
		due_date: str | None = None,
		invoice_number: str | None = None,
		pay_load: dict[str, Any] | None = None,
		redirection_urls: RedirectionUrls | None = None,
	) -> EinvoiceCreationResult:
		"""Creates an e-invoice"""
		if customer.customer_unique_id is None:
			raise FawaterakValidationException(
				"customer_unique_id is necessary.", status_code=400
			)

		payload: dict[str, Any] = {
			"currency": currency,
			"cartTotal": cart_total,
			"customer": customer.to_dict(),
			"cartItems": [item.to_dict() for item in cart_items],
		}

		if due_date is not None:
			payload["due_date"] = due_date
		if invoice_number is not None:
			payload["invoice_number"] = invoice_number
		if pay_load is not None:
			payload["payLoad"] = pay_load
		if redirection_urls is not None:
			payload["redirectionUrls"] = redirection_urls.to_dict()

		response = self._http.request("POST", "/api/v3/createEinvoice", json=payload)
		data = response.get("data", {})

		return EinvoiceCreationResult.from_dict(data)

	def get_einvoice(self, invoice_id: int) -> EInvoice:
		"""Gets a specific e-invoice based on invoice_id"""
		payload = {"invoice_id": invoice_id}

		response = self._http.request("POST", "/api/v3/invoice/get", json=payload)
		data = response.get("data", {})

		return EInvoice.from_dict(data)

	def list_einvoices(
		self, einvoice_filter: EinvoiceFilter | None = None
	) -> Page[EInvoice]:
		"""
		Lists e-invoice based on filter (if found).

		Returns in paginated response in pages of 10.
		"""
		payload = {}

		if einvoice_filter is not None:
			payload["filter"] = einvoice_filter.to_dict()

		response = self._http.request("POST", "/api/v3/invoice/index", json=payload)
		page = response.get("data", {})
		data = page.get("data", {})
		items = [EInvoice.from_dict(item) for item in data]

		return Page(
			data=items,
			per_page=int(page.get("per_page", 0)),
			total=int(page.get("total", 0)),
			current_page=int(page.get("current_page", 0)),
			last_page=int(page.get("last_page", 0)),
			from_item=int(page.get("from")) if page.get("from") is not None else None,
			to_item=int(page.get("to")) if page.get("to") is not None else None,
		)

	def update_einvoice(
		self,
		*,
		invoice_id: int,
		customer: Customer,
		currency: str | None = None,
		products: list[CartItem] | None = None,
		has_history: bool = False,
		due_date: str | None = None,
		invoice_number: str | None = None,
		tags: str | None = None,
	) -> EInvoice:
		"""
		Updates an existing e-invoice. When has_history is not set, currency and products are required and line items are replaced.

		"""
		if customer.customer_unique_id is None:
			raise FawaterakValidationException(
				"customer_unique_id is necessary.", status_code=400
			)

		payload = {"invoice_id": invoice_id, "customer": customer.to_dict()}

		if due_date is not None:
			payload["due_date"] = due_date
		if invoice_number is not None:
			payload["invoice_number"] = invoice_number
		if tags is not None:
			payload["tags"] = tags

		if has_history:
			payload["hasHistory"] = True
		else:
			if currency is None or products is None:
				raise FawaterakValidationException(
					"currency and products are required when has_history is False.",
					status_code=400,
				)
			payload["currency"] = currency
			payload["products"] = [item.to_dict() for item in products]

		response = self._http.request("POST", "/api/v3/invoice/update", json=payload)
		data = response.get("data", {})

		return EInvoice.from_dict(data)

	def delete_einvoice(self, invoice_id: int) -> bool:
		"""
		Deletes an unpaid e-invoice.

		The API refuses deletion if active payment references block it.
		(That's what docs say, can't replicate it)
		Returns True on a successful deletion response.  
		
		Can't understand how they don't soft delete, they just go full 
		delete, like not just a status saying deleted (Soft-deletion). 
		"""
		self._http.request(
			"POST",
			"/api/v3/invoice/delete",
			json={"invoice_id": invoice_id},
		)
		return True

	def close(self) -> None:
		self._http.close()

	def __enter__(self) -> FawaterakClient:  # noqa: PYI034   TODO: Update when dropping support for 3.9 & 3.10
		return self

	def __exit__(self, *exc_info: object) -> None:
		self.close()
