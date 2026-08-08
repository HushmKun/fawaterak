# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
