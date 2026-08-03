# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
