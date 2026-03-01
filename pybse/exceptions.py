"""
pybse.exceptions
================
BSE exception hierarchy.
"""


class BSEValidationError(ValueError):
    """Raised before any API call when the caller passes invalid input."""


class BSEApiError(Exception):
    """Raised when BSE returns an error response."""


class AuthenticationFailed(BSEApiError):
    """BSE rejected the credentials."""


class InvestorAlreadyExists(BSEApiError):
    """UCC registration failed because the investor already exists in BSE."""


class InvalidPAN(BSEApiError):
    """BSE rejected the PAN."""


class OrderRejected(BSEApiError):
    """BSE rejected the order."""


class BSEUnknownError(BSEApiError):
    """Catch-all for unrecognised BSE error codes.

    Attributes:
        code: The raw error code returned by BSE.
        message: The raw error message returned by BSE.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"BSE error {code}: {message}")
