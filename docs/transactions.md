# Transactions

Fawaterak supports two transaction modes:

- **Hosted checkout** — the customer is redirected to a Fawaterak-hosted page to
  select a payment method and complete the purchase.
- **Direct payment** — you pre-select the payment method and receive
  provider-specific data synchronously (reference code, wallet request, card
  redirect, etc.).

## Hosted checkout

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

## Direct payment

Pass a `payment_method_id` from `get_payment_methods()` to pay with a specific
method. The response returns provider-specific data in `result.payment_data`.

```python
from fawaterak import (
	CardPaymentResult,
	MobileWalletResult,
	ReferenceCodeResult,
)

result = client.create_transaction(
	currency="EGP",
	customer=Customer(first_name="Ahmed", last_name="Ali"),
	cart_items=[CartItem(name="Order total", price=100.0, quantity=1)],
	cart_total=100.0,
	payment_method_id=3,  # e.g. Fawry
)

payment = result.payment_data
if isinstance(payment, ReferenceCodeResult):
	print(payment.reference_number)
elif isinstance(payment, CardPaymentResult):
	print(payment.redirect_to)
elif isinstance(payment, MobileWalletResult):
	print(payment.iso_qr)
```

## Fetch and list transactions

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
