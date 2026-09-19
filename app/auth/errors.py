class UnauthenticatedError(Exception):
    """Raised when a request has no valid Clerk session token."""


class AuthenticationConfigurationError(Exception):
    """Raised when a protected route cannot authenticate safely."""
