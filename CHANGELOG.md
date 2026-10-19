# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.2] - 2026-10-19

### Fixed

- `import fawaterak` failed on Python 3.9 and 3.10 in every release since
  0.2.0. `fawaterak._http` imported `typing_extensions`, which is not a
  declared dependency, and on 3.9 `fawaterak.webhooks.parsers` also built
  `WebhooksParseResult` with a runtime `X | Y` union (3.10+ only). Neither
  remains, so no new runtime dependency is needed.
- The CI matrix only ever ran the runner's default Python (3.12):
  `astral-sh/setup-uv@v3` ignored its `python-version` input. CI now uses
  `setup-uv@v10.3.0`, which honors the input, and runs ruff/ty once in a 
  separate `lint` job.

### Added

- `py.typed` marker, so type checkers use the SDK's inline type hints.
- CI now tests Python 3.15.
- CI builds the wheel on every supported Python and imports it in a clean
  environment holding only its declared dependencies.

### Modified

- `FawaterakException`, and so every SDK exception, now derives from
  `Exception` instead of `BaseException`. Generic `except Exception:` handlers
  (framework error handlers, retry decorators, task runners) now catch SDK
  errors; `except FawaterakException` code is unaffected. If you relied on SDK
  errors escaping `except Exception`, catch `FawaterakException` before it.
- The build backend now requires `uv_build>=0.13.1,<0.14`.

### Removed

- `python-dotenv` is no longer a runtime dependency; the SDK never imported
  it. If your code uses `dotenv` and only got it through `fawaterak`, add
  `python-dotenv` to your own dependencies.

## [0.5.1] - 2026-10-17

### Modified

- `Config.resolve(environment=...)` is now typed as `Literal["staging",
  "production"]` (`fawaterak.config.Environment`) instead of `str`. Runtime
  behavior is unchanged, but type checkers now flag misspelled environments,
  and callers passing a plain `str` (e.g. a settings value) must narrow or
  `cast` it first.
- Integration tests (`@pytest.mark.integration`) are now deselected by default;
  run them explicitly with `uv run pytest -m integration`.
- Integration test fixtures pin `environment="staging"`, so a shell with
  `FAWATERAK_ENV=production` can no longer send live refunds, invoices, or
  transactions to production.
- `docs/refunds.md`: documents that `create_refund` raises
  `FawaterakValidationException` when the API rejects a refund.
- The staging refund integration test no longer requests page 1 of
  `list_refunds` twice when collecting all pages; a unit test now covers the
  pagination helper.

## [0.5.0] - 2026-10-16

### Added

- Refunds support in `fawaterak.client.FawaterakClient`:
  - `get_refund_types` — localized map of refund type codes to labels.
  - `get_refund_reasons` — valid `reason` strings for refund submission.
  - `create_refund` — submit a partial/full refund with `refund_type`,
    `refund_id`, `reason`, and `refundable_amount`.
  - `list_refunds` — paginated (10/page) refund request list.
  - `get_refund` — fetch one refund request (returns `None` for unknown ids).
  - `delete_refund` — cancel a pending (non-approved) refund request.
- `RefundType` enum exchanging `RefundType` / int / str for the transaction
  code conversion (`"0"`–`"3"`).
- `fawaterak.models.refund`: `RefundRequest`, `RefundCreationResult`, and
  `RefundType`.
- Unit tests and staging integration tests covering the refund surface.

## [0.4.1] - 2026-08-16

### Added

- Unit tests covering the full e-invoice lifecycle and model parsing
  (`tests/test_einvoice.py`).

### Modified

- `README.md`: bumped package version and clarified e-invoicing status.

## [0.4.0] - 2026-08-16

### Added

- E-invoicing support in `fawaterak.client.FawaterakClient`:
  - `create_einvoice` — create a multi-attempt payment link.
  - `get_einvoice` — fetch one e-invoice by `invoice_id`.
  - `list_einvoices` — list e-invoices with an optional `EinvoiceFilter`.
  - `update_einvoice` — replace line items (default) or update metadata while
    preserving history (`has_history=True`).
  - `delete_einvoice` — soft-delete an unpaid e-invoice.
- E-invoice models in `fawaterak.models.einvoice`: `EInvoice`,
  `EinvoiceCreationResult`, `EinvoiceProduct`, and `EinvoiceFilter`.
- Unit tests and staging integration tests covering the full e-invoice
  lifecycle.

## [0.3.1] - 2026-08-09

### Modified

- `fawaterak._http` module to set `Authorization`, `Accept`, `Content-Type`
  and `User-Agent` headers once on the session, and to rebuild the session
  after token refresh so that retried requests carry the new access token.
- `fawaterak.auth` module to create its own `requests.Session` with a
  `User-Agent` header that identifies the SDK version and platform; the
  constructor no longer requires an external session instance.
- `fawaterak.client` module to stop passing a raw `requests.Session` to
  `TokenManager`, relying on the auth module’s internal session instead.

## [0.3.0] - 2026-08-08

### Added

- `fawaterak.webhooks` module with framework-agnostic HMAC verification and
  typed event parsers.
- `WebhookType` enum and per-type `verify_*_webhook` / `parse_*_webhook`
  functions, plus generic `verify_webhook` / `parse_webhook` dispatchers.
- Webhook event dataclasses: `PaidWebhookEvent`, `FailedWebhookEvent`,
  `CancelWebhookEvent`, `RefundWebhookEvent`, and `TokenizationWebhookEvent`.
- Normalization of both Trx-style (`transaction_key`/`transaction_id`) and
  legacy invoice-style (`invoice_key`/`invoice_id`) fields into flat event
  models for paid and failed webhooks.
- Tokenization webhook verification/parser stub that raises
  `NotImplementedError` until Later Phase.
- README section with Flask, Django-style, and FastAPI-style webhook examples.

## [0.2.0] - 2026-08-05

### Added

- `FawaterakClient` with `get_payment_methods`, `create_transaction`,
  `get_transaction`, and `list_transactions` methods.
- Request models: `Customer`, `CartItem`, `RedirectionUrls`, `TaxData`,
  `DiscountData`.
- Response models: `PaymentMethod`, `TransactionResult`,
  `HostedCheckoutResult`, `DirectPaymentResult`, `TransactionData`,
  `TransactionExportItem`, and `Page`.
- Discriminated `PaymentResult` union (`CardPaymentResult`,
  `ReferenceCodeResult`, `MobileWalletResult`, `UnknownPaymentResult`) built by
  `parse_payment_data` based on response keys.
- Unit tests for models and client, plus a staging integration test behind
  `@pytest.mark.integration`.

## [0.1.0] - 2026-08-03

### Added

- Initial project scaffolding and `pyproject.toml`.
- `Config` singleton with explicit-argument and environment-variable resolution.
- `TokenManager` for OAuth2 `client_credentials` and `refresh_token` flows with
  expiry-aware caching and thread-safe refresh.
- `HTTPClient` for authenticated requests, transport-level retries, and
  Fawaterak-specific error mapping.
- Exception hierarchy: `FawaterakException`, `FawaterakAPIException`,
  `FawaterakAuthException`, `FawaterakConnectionException`,
  `FawaterakConfigException`, `FawaterakValidationException`,
  `FawaterakWebhookException`, and `FawaterakTemporaryException`.
- Test suite covering `Config` and `TokenManager`.
- `README.md`, `CHANGELOG.md`, and `LICENSE`.
