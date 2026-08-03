"""
Fawaterak SDK exception module.

```
FawaterakError
├── FawaterakConnectionError        # network/timeout, safe to retry
├── FawaterakWebhookError           # signature mismatch / malformed webhook body
└── FawaterakAPIError               # non-2xx with parsed {status, message} body
    ├── FawaterakAuthError          # 401 (after one failed refresh-and-retry)
    ├── FawaterakValidationError    # 400/422
    └── FawaterakTemporaryError     # 503 — safe to retry with backoff
```
"""


class FawaterakException(BaseException):
	"""Base class for every exception the SDK raises"""


class FawaterakConfigException(FawaterakException):
	"""The SDK was misconfigured — missing credentials, an unrecognized environment."""


class FawaterakConnectionException(FawaterakException):
	"""Network-level exception where no response was received"""


class FawaterakWebhookException(FawaterakException):
	"""Webhook failed signature verification or parsing"""


class FawaterakAPIException(FawaterakException):
	"""Fawaterak API returned a non-2xx response"""

	def __init__(
		self, message: str, status_code: int, raw_body: dict | str | None = None
	) -> None:
		super().__init__(message)
		self.message: str = message
		self.status_code: int = status_code
		self.raw_body: dict | str | None = raw_body


class FawaterakAuthException(FawaterakAPIException):
	"""Error 401: OAuth failed even after refresh and retry (Bad Credentials)"""


class FawaterakValidationException(FawaterakAPIException):
	"""Error 400/422: bad request, non-retryable as-is"""


class FawaterakTemporaryException(FawaterakAPIException):
	"""Error 503: transient safe to retry with backoff"""
