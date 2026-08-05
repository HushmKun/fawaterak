"""fawaterak — unofficial Python SDK for the Fawaterak API v3."""

from importlib.metadata import PackageNotFoundError, version

from .client import FawaterakClient
from .config import Config
from .exceptions import (
	FawaterakAPIException,
	FawaterakAuthException,
	FawaterakConfigException,
	FawaterakConnectionException,
	FawaterakException,
	FawaterakTemporaryException,
	FawaterakValidationException,
	FawaterakWebhookException,
)
from .models import (
	CardPaymentResult,
	CartItem,
	Customer,
	DirectPaymentResult,
	DiscountData,
	HostedCheckoutResult,
	MobileWalletResult,
	Page,
	PaymentMethod,
	PaymentMethodHistoryItem,
	PaymentResult,
	RedirectionUrls,
	ReferenceCodeResult,
	TaxData,
	TransactionData,
	TransactionExportItem,
	TransactionResult,
	UnknownPaymentResult,
	parse_payment_data,
)

try:
	__version__ = version("fawaterak")
except PackageNotFoundError:
	__version__ = "unknown"

__all__ = [
	"__version__",
	"FawaterakClient",
	"Config",
	"FawaterakException",
	"FawaterakConfigException",
	"FawaterakConnectionException",
	"FawaterakWebhookException",
	"FawaterakAPIException",
	"FawaterakAuthException",
	"FawaterakValidationException",
	"FawaterakTemporaryException",
	"CartItem",
	"Customer",
	"DiscountData",
	"RedirectionUrls",
	"TaxData",
	"PaymentMethod",
	"CardPaymentResult",
	"DirectPaymentResult",
	"HostedCheckoutResult",
	"MobileWalletResult",
	"Page",
	"PaymentMethodHistoryItem",
	"PaymentResult",
	"ReferenceCodeResult",
	"TransactionData",
	"TransactionExportItem",
	"TransactionResult",
	"UnknownPaymentResult",
	"parse_payment_data",
]
