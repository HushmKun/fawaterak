# API reference

This page is generated from the SDK source docstrings.

## Client

::: fawaterak.client.FawaterakClient
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members:
        - get_payment_methods
        - create_transaction
        - get_transaction
        - list_transactions
        - create_einvoice
        - get_einvoice
        - list_einvoices
        - update_einvoice
        - delete_einvoice
        - parse_paid_webhook
        - parse_failed_webhook
        - parse_cancel_webhook
        - parse_refund_webhook
        - parse_webhook

## Configuration

::: fawaterak.config.Config
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

## Models

::: fawaterak.models.common.Customer
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

::: fawaterak.models.common.CartItem
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

::: fawaterak.models.common.RedirectionUrls
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

::: fawaterak.models.einvoice.EInvoice
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

::: fawaterak.models.einvoice.EinvoiceCreationResult
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

::: fawaterak.models.einvoice.EinvoiceFilter
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false

## Exceptions

::: fawaterak.exceptions
    options:
      show_source: false
      show_root_heading: true
      show_root_full_path: false
      members:
        - FawaterakException
        - FawaterakAPIException
        - FawaterakAuthException
        - FawaterakConfigException
        - FawaterakConnectionException
        - FawaterakTemporaryException
        - FawaterakValidationException
        - FawaterakWebhookException
