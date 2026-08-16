# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
