"""Exceptions for the pub/sub service."""

class PubSubError(Exception):
    """Base exception for pub/sub errors."""
    pass


class PubSubConnectionError(PubSubError):
    """Raised when there is an error connecting to the pub/sub backend."""
    pass


class PubSubPublishError(PubSubError):
    """Raised when there is an error publishing a message."""
    pass


class PubSubSubscribeError(PubSubError):
    """Raised when there is an error subscribing to a channel."""
    pass


class PubSubUnsubscribeError(PubSubError):
    """Raised when there is an error unsubscribing from a channel."""
    pass


class PubSubTimeoutError(PubSubError):
    """Raised when an operation times out."""
    pass


class PubSubClosedError(PubSubError):
    """Raised when attempting to use a closed pub/sub connection."""
    pass


__all__ = [
    'PubSubError',
    'PubSubConnectionError',
    'PubSubPublishError',
    'PubSubSubscribeError',
    'PubSubUnsubscribeError',
    'PubSubTimeoutError',
    'PubSubClosedError',
]