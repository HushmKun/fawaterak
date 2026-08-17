# Error handling

The SDK maps API and transport failures to a typed exception hierarchy rooted at
`FawaterakException`.

## Exception hierarchy

```
FawaterakException
├── FawaterakConnectionException  # network/timeout failures
├── FawaterakAPIException         # non-2xx API responses
│   ├── FawaterakAuthException    # 401 after one retry
│   ├── FawaterakValidationException  # 400 / 422
│   └── FawaterakTemporaryException   # 503 and other transient errors
└── FawaterakWebhookException     # webhook signature mismatch
```

## Handling errors

```python
from fawaterak import FawaterakClient
from fawaterak.exceptions import (
	FawaterakValidationException,
	FawaterakAuthException,
	FawaterakConnectionException,
)

client = FawaterakClient()

try:
	client.create_transaction(...)
except FawaterakValidationException as exc:
	print(f"Validation failed ({exc.status_code}): {exc.message}")
except FawaterakAuthException:
	print("Authentication failed — check credentials")
except FawaterakConnectionException:
	print("Network error — retry later")
```

## Authentication retry

`HTTPClient` automatically refreshes the OAuth access token on the first `401`
and retries the request once. If the retry also fails, it raises
`FawaterakAuthException`.

## Transient errors

`FawaterakTemporaryException` is raised for `503` responses and other transient
conditions. These are safe to retry with backoff.
