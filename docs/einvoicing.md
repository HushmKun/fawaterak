# E-invoicing

E-invoices are shareable, multi-attempt payment links. The customer can pay at
any time within the due date and retry with different payment methods.

## Create an e-invoice

`customer_unique_id` is required for e-invoices.

```python
from fawaterak import CartItem, Customer

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
print(created.invoice_key)
print(created.invoice_id)
```

## Get and list e-invoices

```python
invoice = client.get_einvoice(created.invoice_id)
print(invoice.status)

page = client.list_einvoices()
for item in page.data:
	print(item.invoice_id, item.status)
```

You can also filter the list:

```python
from fawaterak import EinvoiceFilter

page = client.list_einvoices(EinvoiceFilter(status=2, invoice_number="INV-001"))
```

## Update an e-invoice

### Replace line items

By default, `update_einvoice` requires `currency` and `products`. The existing
line items are replaced with the new cart.

```python
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
```

### Preserve history

Pass `has_history=True` to update metadata without resending the cart. The API
keeps the existing line items and skips currency/product validation.

```python
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
```

## Delete an e-invoice

```python
client.delete_einvoice(created.invoice_id)
```

The API only allows deletion when no active payment references block it.
