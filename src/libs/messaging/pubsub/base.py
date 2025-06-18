from abc import ABC, abstractmethod
from typing import Callable, Dict


class PubSubClient(ABC):
    """
    An abstract client for a classic, fire-and-forget Pub/Sub messaging model.

    This is best used for transient, real-time notifications where persistence
    is not required. If a subscriber is not online, it will miss the message.
    """

    @abstractmethod
    def publish(self, channel: str, message: Dict) -> None:
        """Publishes a message to a specific channel (topic)."""
        pass

    @abstractmethod
    def subscribe(self, channel: str, callback: Callable[[Dict], None]) -> None:
        """
        Subscribes to a channel and executes the callback for each message.
        This is a non-blocking call that registers the subscription.
        """
        pass

    @abstractmethod
    def listen(self) -> None:
        """
        Starts a blocking loop to listen for messages on subscribed channels.
        This should typically be run in a separate thread or process.
        """
        pass