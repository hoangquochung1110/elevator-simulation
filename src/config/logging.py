import structlog


def configure_logging():
    """
    Set up structured JSON logging for the application using structlog.

    This configures the standard logging module to emit plain messages,
    then initializes structlog with processors to:
      1. Timestamp logs in ISO format.
      2. Include log level and stack information.
      3. Format exception info when present.
      4. Render final output as JSON for easy ingestion into log systems.

    This function is idempotent and safe to call multiple times.
    """
    import logging
    import sys

    # Get the root logger
    root_logger = logging.getLogger()

    # Return early if already configured
    if hasattr(configure_logging, '_configured'):
        return

    # Remove all existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure basic logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Mark as configured
    configure_logging._configured = True

