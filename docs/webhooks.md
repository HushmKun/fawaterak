# Webhooks

Fawaterak sends server-to-server POST notifications to your endpoints. The SDK
verifies webhook HMAC signatures using your **vendor API key**, not the OAuth
client secret.

## Configuration

Provide `vendor_api_key` to `Config.resolve()` or set `FAWATERAK_VENDOR_API_KEY`.

```python
from fawaterak import Config, FawaterakClient

config = Config.resolve(
	client_id="...",
	client_secret="...",
	environment="staging",
	vendor_api_key="your-vendor-api-key",
)
client = FawaterakClient(config=config)
```

## Framework examples

### Flask

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

### Django

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

### FastAPI

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

## Event fields

Paid webhooks carry settlement details on top of the payment status:

| Field | Meaning |
|-------|---------|
| `fees` | Fee charged on the payment |
| `card_discount_amount`, `discount_bank_code` | Bank card discount, when one applied |
| `payment_token` | Saved card token, for tokenization flows |
| `financial_breakdown` | A `FinancialBreakdown`: original, converted, fee and settlement amounts. Only sent once the payment is settled. |

```python
event = client.parse_paid_webhook(payload)

if event.financial_breakdown is not None:
	print(event.financial_breakdown.settlement_amount)
	print(event.financial_breakdown.settlement_currency)
```

Every event also keeps the signature it was verified with: `hash_key`, plus
`transaction_hash_key` on paid webhooks.

Any of these fields is `None` when the payload omits it, for example on a
pending paid webhook. The legacy `api_key` field some integrations send is
never copied onto an event, so it cannot leak through `repr()` or logs; read
it from the raw payload if you need it.

## Other webhook types

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

Paid and failed webhooks can be delivered as JSON or form-urlencoded; cancel
and refund webhooks are always JSON. The parsers raise
`FawaterakWebhookException` if the signature does not match.

You can also call the standalone functions in `fawaterak.webhooks` directly if
you prefer not to instantiate `FawaterakClient` for webhook handlers.
