# fawaterak

> **Unofficial** Python SDK for the [Fawaterak](https://fawaterk.com/) API.

**This project is not affiliated with, endorsed by, or sponsored by Fawaterak.**
It is a community-maintained, unofficial SDK written by independent developers.
The maintainers have no business relationship with the company Fawaterak.
Use this library at your own risk.

## Status

This project is in early development (`0.4.0`). The foundational OAuth/HTTP
layers, the core transaction client (payment methods, create/fetch/list
transactions), the framework-agnostic webhook verification/parsers, and
e-invoicing are implemented. Refunds and tokenization are still on the roadmap.

## Features

- **Explicit configuration** via constructor arguments or environment variables.
- **OAuth2 token management** (`client_credentials` + `refresh_token` flows) with
  automatic caching and expiry-aware renewal.
- **Thread-safe token refresh** so concurrent callers do not issue duplicate
  `/oauth/token` requests.
- **Central HTTP client** with bearer-token injection, transport-level retries, and
  Fawaterak-specific error mapping.
- **Exception hierarchy** for network, authentication, validation, and transient
  API errors.
- **`FawaterakClient`** with `get_payment_methods`, `create_transaction`,
	`get_transaction`, and `list_transactions` covering the core transaction flow.
- **E-invoicing** with `create_einvoice`, `get_einvoice`, `list_einvoices`,
	`update_einvoice`, and `delete_einvoice` for shareable, multi-attempt payment
	links.
- **Webhook verification and parsing** with HMAC signature checks and typed

  event dataclasses (`PaidWebhookEvent`, `FailedWebhookEvent`,
  `CancelWebhookEvent`, `RefundWebhookEvent`).
- **Two transaction modes** — hosted checkout (`result.url`) and direct payment
  (`result.payment_data`), with a discriminated `PaymentResult` union for card
  redirects, reference codes (Fawry/Aman/Masary), and mobile wallets.
- **Typed dataclass models** (`Customer`, `CartItem`, `TransactionData`, `Page`,
  etc.) that serialize to the exact API payload shapes.

## Installation

```bash
pip install fawaterak
```

Or with `uv`:

```bash
uv add fawaterak
```

## Quick start

```python
from fawaterak import Config, FawaterakClient

conf = Config.resolve(
	client_id="your-client-id",
	client_secret="your-client-secret",
	environment="staging",  # or "production"
)

client = FawaterakClient(config=conf)
methods = client.get_payment_methods()
print([method.name_en for method in methods])
```

## Configuration

`Config.resolve()` accepts explicit arguments and falls back to environment
variables. Explicit arguments always win.

| Setting           | Environment variable        | Required |
|-------------------|-----------------------------|----------|
| `client_id`       | `FAWATERAK_CLIENT_ID`       | Yes      |
| `client_secret`   | `FAWATERAK_CLIENT_SECRET`   | Yes      |
| `environment`     | `FAWATERAK_ENV`             | Yes*     |
| `base_url`        | —                           | Yes*     |
| `vendor_api_key`  | `FAWATERAK_VENDOR_API_KEY`  | No**     |

\* Either `environment` (`staging` or `production`) or a direct `base_url` must
be provided.

\** Must be provided if you plan to use Webhooks.

## Usage

### Hosted checkout

Omit `payment_method_id` to create a payment link and redirect the customer to
the Fawaterak-hosted checkout page.

```python
from fawaterak import CartItem, Customer, RedirectionUrls

result = client.create_transaction(
	currency="EGP",
	customer=Customer(
		first_name="Ahmed",
		last_name="Ali",
		email="ahmed@example.com",
	),
	cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
	cart_total=100.0,
	redirection_urls=RedirectionUrls(
		success_url="https://yoursite.com/success",
		fail_url="https://yoursite.com/fail",
	),
)

# result is a HostedCheckoutResult
redirect_url = result.url
```

### Direct payment

Pass a `payment_method_id` from `get_payment_methods()` to pay with a specific
method. The response returns provider-specific data in `result.payment_data`.

```python
result = client.create_transaction(
	currency="EGP",
	customer=Customer(first_name="Ahmed", last_name="Ali"),
	cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
	cart_total=100.0,
	payment_method_id=3,  # e.g. Fawry
)

from fawaterak import (
	CardPaymentResult,
	MobileWalletResult,
	ReferenceCodeResult,
)

payment = result.payment_data
if isinstance(payment, ReferenceCodeResult):
	print(payment.reference_number)
elif isinstance(payment, CardPaymentResult):
	print(payment.redirect_to)
elif isinstance(payment, MobileWalletResult):
	print(payment.iso_qr)
```

### Fetch and list transactions

```python
from datetime import date

transaction = client.get_transaction(intent_key="550e8400-e29b-41d4-a716-446655440000")
print(transaction.status_text)

page = client.list_transactions(
	start_date=date(2026, 1, 1),
	end_date=date(2026, 1, 31),
	per_page=15,
)
for item in page.data:
	print(item.transaction_id, item.status_text)
```

## E-invoicing

Create and manage multi-attempt payment links. The customer can pay at any time
within the due date and retry with different payment methods.

```python
from fawaterak import CartItem, Customer
from datetime import date

# Create an e-invoice (requires customer_unique_id)
created = client.create_einvoice(
	currency="EGP",
	customer=Customer(
		first_name="Ahmed",
		last_name="Ali",
		customer_unique_id="user_12345",
	),
	cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
	cart_total=100.0,
)
print(created.url)  # hosted payment link

# Fetch, list, update, and delete
invoice = client.get_einvoice(created.invoice_id)

page = client.list_einvoices()
for item in page.data:
	print(item.invoice_id, item.status)

# Replace line items (default; requires currency + products)
updated = client.update_einvoice(
	invoice_id=created.invoice_id,
	customer=Customer(
		first_name="Ahmed",
		last_name="Ali",
		customer_unique_id="user_12345",
	),
	currency="EGP",
	products=[CartItem(name="Updated item", price=200.0, quantity=2)],
)

# Update metadata only, preserving existing line items
metadata = client.update_einvoice(
	invoice_id=created.invoice_id,
	customer=Customer(
		first_name="Ahmed",
		last_name="Ali",
		customer_unique_id="user_12345",
	),
	has_history=True,
	invoice_number="INV-001",
	tags="monthly",
)

client.delete_einvoice(created.invoice_id)
```

`has_history=True` tells the API to skip currency/product validation and keep
the existing line items, so you can update fields like `invoice_number` or
`tags` without resending the cart.

## Webhooks

The SDK verifies webhook HMAC signatures using your **vendor API key** (not the
OAuth client secret). It is framework-agnostic: parse the incoming body into a
dict using your web framework, then call the provided parser.

### Flask example (paid webhook)

```python
from fawaterak import FawaterakClient

client = FawaterakClient()


@app.post("/webhooks/fawaterak/paid/")
def handle_paid_webhook():
	payload = request.get_json() or request.form.to_dict()
	event = client.parse_paid_webhook(payload)

	if event.status == "paid":
		fulfill_order(event)

	return "OK", 200
```

### Django example

```python
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from fawaterak import FawaterakClient

client = FawaterakClient()


@csrf_exempt
def fawaterak_paid_webhook(request):
	payload = request.POST if request.method == "POST" else request.json()
	event = client.parse_paid_webhook(payload)

	if event.status == "paid":
		fulfill_order(event)

	return JsonResponse({"status": "ok"})
```

### FastAPI example

```python
from fastapi import FastAPI, Request
from fawaterak import FawaterakClient

app = FastAPI()
client = FawaterakClient()


@app.post("/webhooks/fawaterak/paid/")
async def handle_paid_webhook(request: Request):
	payload = await request.json()
	event = client.parse_paid_webhook(payload)

	if event.status == "paid":
		fulfill_order(event)

	return {"status": "ok"}
```

### Other webhook types

```python
# Failed payment
failed_event = client.parse_failed_webhook(payload)

# Cancelled / expired reference
cancel_event = client.parse_cancel_webhook(payload)

# Refund approved
refund_event = client.parse_refund_webhook(payload)

# Dispatch by type when the endpoint handles multiple webhook kinds
from fawaterak.webhooks import WebhookType

event = client.parse_webhook(payload, WebhookType.REFUND)
```

You can also call the standalone functions in `fawaterak.webhooks` directly if
you prefer not to instantiate `FawaterakClient` for webhook handlers.

Paid and failed webhooks can be delivered as JSON or form-urlencoded; cancel
and refund webhooks are always JSON. The parsers raise
`FawaterakWebhookException` if the signature does not match. The generic
`verify_webhook`/`parse_webhook` dispatchers raise `FawaterakWebhookException`
for unknown webhook types.

## Development

This project uses `uv` for dependency management.

```bash
# Install dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest

# Run live integration tests against staging (requires real credentials)
uv run pytest -m integration

# Run linters and type checker
uv run ruff check .
uv run ruff format --check .
uv run ty check .
```

## License

This project is licensed under the GNU Affero General Public License v3.0 or
later (AGPL-3.0+). See [LICENSE](./LICENSE) for the full text.