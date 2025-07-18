"""
Redis Pub/Sub channel definitions for the elevator simulator.
This module contains the centralized definitions of all channel names used
in the system to ensure consistency between publishers and subscribers.
"""
# Channel for sending commands to a specific elevator (format with elevator ID)
# Example usage: ELEVATOR_COMMANDS.format(1) -> "elevator:commands:1"
ELEVATOR_COMMANDS = "elevator:commands:{}"

# Channel for receiving status updates from a specific elevator (format with elevator ID)
# Example usage: ELEVATOR_STATUS.format(2) -> "elevator:status:2"
ELEVATOR_STATUS = "elevator:status:{}"

# Channel for system-wide notifications and events
ELEVATOR_SYSTEM = "elevator:system"

# Channel that alternative to ELEVATOR_REQUESTS, using Redis Stream
ELEVATOR_REQUESTS_STREAM = "elevator:requests:stream"

# Channel for sending commands to the scheduler
SCHEDULER_COMMANDS = "scheduler:commands"
