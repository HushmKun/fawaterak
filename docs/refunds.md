# Refunds

Submit and manage refund requests for paid invoices and transactions through
`/api/v3/refund/*` (OAuth client credentials, same as all v3 endpoints).

## The refund flow

1. `get_refund_types` / `get_refund_reasons` — discover valid codes and reasons.
2. `create_refund` — submit a partial or full refund request.
3. `list_refunds` / `get_refund` — poll the request's status.
4. `delete_refund` — cancel a **pending** request (approved refunds cannot be
   deleted).

## Discover refund types and reasons

`refund_type` says which record kind `refund_id` points at:

| Code | `RefundType` member | meaning |
|------|---------------------|---------|
| `0` | `RefundType.INVOICE` | invoice id |
| `1` | `RefundType.PAYMENT_LINK_TRANSACTION` | payment link transaction id |
| `2` | `RefundType.COLLECTION_LINK_TRANSACTION` | collection link transaction id |
| `3` | `RefundType.INTEGRATION_TRANSACTION` | transaction created through the API |

```python
from fawaterak import RefundType

types = client.get_refund_types()
# {"0": "invoice", "1": "Payment link transaction", ...}

reasons = client.get_refund_reasons()
# ["Product not available", "Customer changed their mind", ...]
```

## Create a refund

`reason` must be one of the strings from `get_refund_reasons()`, and
`refundable_amount` must not exceed the remaining refundable balance.

```python
from fawaterak import RefundType

result = client.create_refund(
	refund_type=RefundType.INTEGRATION_TRANSACTION,
	refund_id=3485,  # transaction id
	reason="Customer changed their mind",
	refundable_amount=100.0,  # partial refunds are allowed
	comment="Damaged item order #1001",
)
print(result.message)  # "Refunded successfully"
```

`refund_type` also accepts the raw int (`3`) or string code (`"3"`) for
convenience.

If the API rejects the refund (amount over the remaining balance, a reason
not in `get_refund_reasons()`, or a `refund_id` that doesn't exist or isn't
yours), it answers HTTP 400 and `create_refund` raises
`FawaterakValidationException` carrying the API's `message`. An unknown
`refund_type` raises the same exception before any request is sent.

## List and inspect refund requests

```python
page = client.list_refunds(page=1)
for refund in page.data:
	print(refund.id, refund.status, refund.refundable_amount, refund.can_delete)

# Or fetch one directly:
refund = client.get_refund(827)
print(refund.status)  # "pending" or "approved"
```

Notes:

- Listing is paginated by the API (10 per page), Laravel-style.
- `refundable_amount` is returned as a string on the wire; the SDK parses it
  to `float`.
- `get_refund` returns `None` instead of raising for an unknown id
  (the API answers 200 with an empty object).

## Cancel a pending refund

```python
client.delete_refund(42)  # True on success; only pending requests can be deleted
```

The API refuses to delete approved requests (raises
`FawaterakValidationException`).

!!! note
	On staging, refund requests are auto-approved instantly, so a freshly
	created refund is usually already `approved` and `can_delete` is `False`.
