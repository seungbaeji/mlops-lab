import logging
from contextlib import AbstractContextManager, nullcontext

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import (
    NoOpTracerProvider,
    Span,
    Tracer,
    get_current_span,
)


def init_tracing(service_name: str, trace_endpoint: str) -> None:
    """
    Initialize OpenTelemetry TracerProvider with OTLP exporter.

    Args:
        service_name (str): Name of the service for tracing resource.
        trace_endpoint (str): OTLP trace collector endpoint URL.

    Examples:
        >>> init_tracing("my_service", "http://localhost:4318/v1/traces")
    """
    if not trace_endpoint:
        logging.warning("No trace endpoint configured. Tracing disabled.")
        return

    try:
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=trace_endpoint))
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logging.info("Tracing initialized.")
    except Exception:
        logging.exception("Failed to initialize tracing. Tracing will be disabled.")
        trace.set_tracer_provider(NoOpTracerProvider())


def get_tracer(service_name: str) -> Tracer:
    """
    Return a tracer for the given service name. If tracing is not initialized, returns a no-op tracer.

    Args:
        service_name (str): Name of the service.

    Returns:
        Tracer: OpenTelemetry tracer instance.

    Examples:
        >>> tracer = get_tracer("my_service")
        >>> with tracer.start_as_current_span("my_span"):
        ...     # do something
    """
    try:
        return trace.get_tracer(service_name)
    except Exception:
        trace.set_tracer_provider(NoOpTracerProvider())
        return trace.get_tracer(service_name)


def span_context(tracer: Tracer | None, name: str) -> AbstractContextManager[Span]:
    """
    Returns a context manager for a named tracing span.
    If tracer is None, returns a nullcontext.

    Args:
        tracer (Optional[Tracer]): OpenTelemetry tracer instance or None.
        name (str): Name of the span.

    Returns:
        AbstractContextManager[Span]: Context manager for the span.

    Examples:
        >>> tracer = get_tracer("my_service")
        >>> with span_context(tracer, "my_span"):
        ...     # do something
    """
    if tracer:
        return tracer.start_as_current_span(name)
    return nullcontext(get_current_span())
