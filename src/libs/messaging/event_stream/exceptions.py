"""Exceptions for the event stream service."""


class EventStreamError(Exception):
    """Base exception for event stream errors."""

    pass


class EventStreamConnectionError(EventStreamError):
    """Raised when there is an error connecting to the event stream backend."""

    pass


class EventStreamPublishError(EventStreamError):
    """Raised when there is an error publishing an event."""

    pass


class EventStreamSubscribeError(EventStreamError):
    """Raised when there is an error subscribing to a stream."""

    pass


class EventStreamUnsubscribeError(EventStreamError):
    """Raised when there is an error unsubscribing from a stream."""

    pass


class EventStreamTimeoutError(EventStreamError):
    """Raised when an operation times out."""

    pass


class EventStreamClosedError(EventStreamError):
    """Raised when attempting to use a closed event stream connection."""

    pass


__all__ = [
    "EventStreamError",
    "EventStreamConnectionError",
    "EventStreamPublishError",
    "EventStreamSubscribeError",
    "EventStreamUnsubscribeError",
    "EventStreamTimeoutError",
    "EventStreamClosedError",
]
