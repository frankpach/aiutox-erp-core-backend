"""Custom exceptions for Pub-Sub module."""


class PubSubError(Exception):
    """Base exception for Pub-Sub errors."""

    pass


class StreamNotFoundError(PubSubError):
    """Raised when a stream is not found."""

    pass


class GroupNotFoundError(PubSubError):
    """Raised when a consumer group is not found."""

    pass


class PublishError(PubSubError):
    """Raised when event publication fails."""

    pass


class ConsumeError(PubSubError):
    """Raised when event consumption fails."""

    pass



