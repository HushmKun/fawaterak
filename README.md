# fawaterak

> **Unofficial** Python SDK for the [Fawaterak](https://fawaterk.com/) API.

**This project is not affiliated with, endorsed by, or sponsored by Fawaterak.**
It is a community-maintained, unofficial SDK written by independent developers.
The maintainers have no business relationship with the company Fawaterak.
Use this library at your own risk.

## Status

This project is in early development (`0.1.0`). The current release covers the
foundational OAuth and HTTP layers only. Higher-level resource clients (payments,
invoices, refunds, webhooks, etc.) are not yet implemented.

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
from fawaterak.config import Config
from fawaterak.auth import TokenManager
import requests

conf = Config.resolve(
	client_id="your-client-id",
	client_secret="your-client-secret",
	environment="staging",  # or "production"
)

manager = TokenManager(
	conf.client_id,
	conf.client_secret,
	conf.base_url,
	requests.Session(),
)

token = manager.access_token
print(token)
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
| `vendor_api_key`  | `FAWATERAK_VENDOR_API_KEY`  | No       |

\* Either `environment` (`staging` or `production`) or a direct `base_url` must
be provided.

## Development

This project uses `uv` for dependency management.

```bash
# Install dependencies
uv sync --all-extras --dev

# Run tests
uv run pytest

# Run linters and type checker
uv run ruff check .
uv run ruff format --check .
uv run ty check .
```

## License

This project is licensed under the GNU Affero General Public License v3.0 or
later (AGPL-3.0+). See [LICENSE](./LICENSE) for the full text.