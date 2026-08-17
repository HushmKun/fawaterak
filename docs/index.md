---
icon: lucide/rocket
---

# Get started

`fawaterak` is an unofficial Python SDK for the [Fawaterak](https://fawaterk.com/) API v3.

**This project is not affiliated with, endorsed by, or sponsored by Fawaterak.**

## Installation

```bash
uv add fawaterak
```

Or with `pip`:

```bash
pip install fawaterak
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

| Setting          | Environment variable        | Required |
|------------------|-----------------------------|----------|
| `client_id`      | `FAWATERAK_CLIENT_ID`       | Yes      |
| `client_secret`  | `FAWATERAK_CLIENT_SECRET`   | Yes      |
| `environment`    | `FAWATERAK_ENV`             | Yes*     |
| `base_url`       | —                           | Yes*     |
| `vendor_api_key` | `FAWATERAK_VENDOR_API_KEY`  | No**     |

\* Either `environment` (`staging` or `production`) or a direct `base_url` must
be provided.

\** Must be provided if you plan to use webhooks.

## Next steps

- [Transactions](./transactions.md) — hosted checkout and direct payment
- [E-invoicing](./einvoicing.md) — shareable, multi-attempt payment links
- [Webhooks](./webhooks.md) — verify and parse server-to-server events
- [Error handling](./error-handling.md) — exceptions and retries
- [API reference](./api-reference.md) — generated SDK reference
