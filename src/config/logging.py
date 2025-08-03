import enum
import json
import logging
import os
import sys
from typing import Sequence

import structlog
from google.protobuf.json_format import MessageToJson
from opentelemetry import _logs
from opentelemetry._logs import get_logger, set_logger_provider
from opentelemetry.exporter.otlp.proto.common._log_encoder import encode_logs
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import \
    OTLPLogExporter
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import \
    ExportLogsServiceRequest
from opentelemetry.sdk._logs import LogData, LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, LogExporter
from opentelemetry.sdk.resources import Resource


class LogExportResult(enum.Enum):
    SUCCESS = 0
    FAILURE = 1


class OtlpJsonConsoleExporter(OTLPLogExporter):
    """A helper class to export OTLP/JSON."""
    # https://github.com/open-telemetry/opentelemetry-python/issues/4661
    def _translate_data(self, data: Sequence[LogData]) -> ExportLogsServiceRequest:
        return encode_logs(data)

    def shutdown(self):
        pass

    def export(self, batch):
        service_request = self._translate_data(batch)

        json_str = MessageToJson(
            service_request,
            # including_default_value_fields=True,
            preserving_proto_field_name=True,
            indent=None,
        )
        print(json_str)
        return LogExportResult.SUCCESS


def configure_logging():
    """
    Set up structured JSON logging for the application using structlog with OpenTelemetry integration.
    """
    import atexit
    import logging
    import sys

    # Get the root logger
    root_logger = logging.getLogger()

    # Return early if already configured
    if hasattr(configure_logging, '_configured'):
        return root_logger

    # Remove all existing handlers to prevent duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Configure structlog
    structlog.configure(
        processors=[
            # Remove _logger and _name from the event dict
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # Add timestamp
            structlog.processors.TimeStamper(fmt="iso"),
            # Add call site parameters
            structlog.processors.CallsiteParameterAdder(
                [
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                ]
            ),
            # Convert to a format suitable for JSON serialization
            # structlog.processors.ExceptionPrettyPrinter(),
            # Render as JSON - this will be the final output
            structlog.processors.JSONRenderer(sort_keys=True, serializer=json.dumps),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure basic logging to output JSON
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # Set root logger level
    root_logger.setLevel(logging.INFO)

    # Configure OpenTelemetry logging
    try:
        service_name = os.getenv("SERVICE_NAME", "elevator-simulation-unknown")
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.namespace": "elevator-simulation",
            }
        )
        logger_provider = LoggerProvider(resource=resource)

        # Get OTLP endpoint from environment or use default
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        # Configure OTLP gRPC exporter
        log_exporter = OTLPLogExporter(
            endpoint=otlp_endpoint,
            insecure=True,
        )
        # log_exporter = OtlpJsonConsoleExporter(
        #     endpoint=otlp_endpoint,
        #     insecure=True,
        # )

        # Add processor to the logger provider
        logger_provider.add_log_record_processor(
            BatchLogRecordProcessor(log_exporter)
        )

        # Set the global logger provider
        set_logger_provider(logger_provider)

        # Add OpenTelemetry handler to root logger
        otel_handler = LoggingHandler(
            level=logging.INFO,
            logger_provider=logger_provider
        )
        # Don't add any additional handlers - let structlog handle the formatting
        root_logger.addHandler(otel_handler)

        # Ensure proper shutdown
        atexit.register(lambda: logger_provider.shutdown())

    except Exception as e:
        logging.error(f"Failed to configure OpenTelemetry logging: {e}")
        logging.warning("Falling back to basic logging without OpenTelemetry")

    # Mark as configured
    configure_logging._configured = True
    return root_logger
