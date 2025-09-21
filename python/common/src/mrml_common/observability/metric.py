from collections.abc import Hashable, Sequence
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, Info, Summary


class MetricFactory:
    """
    Factory for creating and reusing Prometheus metrics (Counter, Gauge, Histogram, Summary, Info)
    with automatic deduplication by name, type, and labelnames.
    """

    def __init__(self, service_name: str):
        """
        Args:
            service_name (str): Prefix for all metric names (usually the service name).
        """
        self.service_name: str = service_name
        self._metrics: dict[Hashable, Counter | Gauge | Histogram | Summary | Info] = {}

    def _metric_key(
        self,
        metric_type: str,
        name: str,
        labelnames: Sequence[str] | None,
        **kwargs: Any,
    ) -> Hashable:
        """
        Generate a unique key for a metric based on type, name, labelnames, and extra options.

        Args:
            metric_type (str): Metric type (e.g., 'counter', 'gauge').
            name (str): Metric name (without service prefix).
            labelnames (Optional[Sequence[str]]): List of label names.
            **kwargs: Additional keyword arguments for metric uniqueness.

        Returns:
            Hashable: Unique key for metric registry.
        """
        key = (
            metric_type,
            name,
            tuple(labelnames or []),
            tuple(sorted(kwargs.items())) if kwargs else None,
        )
        return key

    def counter(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Counter:
        """
        Create or get a Prometheus Counter metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.

        Returns:
            Counter: Prometheus Counter metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> counter = metrics.counter("requests_total", "Total requests", ["endpoint"])
            >>> counter.labels(endpoint="/api").inc()
        """
        labelnames = labelnames or []
        key = self._metric_key("counter", name, labelnames)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Counter(
            f"{self.service_name}_{name}", documentation, labelnames=labelnames
        )
        self._metrics[key] = metric
        return metric

    def histogram(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] | None = None,
        buckets: Sequence[float] | None = None,
    ) -> Histogram:
        """
        Create or get a Prometheus Histogram metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.
            buckets (Optional[Sequence[float]]): Histogram buckets.

        Returns:
            Histogram: Prometheus Histogram metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> hist = metrics.histogram("latency_seconds", "Request latency", ["endpoint"], buckets=[0.1, 0.5, 1, 2, 5])
            >>> hist.labels(endpoint="/api").observe(0.42)
        """
        labelnames = labelnames or []
        key = self._metric_key(
            "histogram", name, labelnames, buckets=tuple(buckets) if buckets else None
        )
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Histogram(
            f"{self.service_name}_{name}",
            documentation,
            labelnames=labelnames,
            buckets=buckets or Histogram.DEFAULT_BUCKETS,
        )
        self._metrics[key] = metric
        return metric

    def gauge(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Gauge:
        """
        Create or get a Prometheus Gauge metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.

        Returns:
            Gauge: Prometheus Gauge metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> gauge = metrics.gauge("in_progress", "In progress requests", ["endpoint"])
            >>> gauge.labels(endpoint="/api").inc()
            >>> gauge.labels(endpoint="/api").dec()
        """
        labelnames = labelnames or []
        key = self._metric_key("gauge", name, labelnames)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Gauge(
            f"{self.service_name}_{name}", documentation, labelnames=labelnames
        )
        self._metrics[key] = metric
        return metric

    def summary(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] | None = None,
        objectives: dict[float, float] | None = None,
        max_age_seconds: int | None = None,
        age_buckets: int | None = None,
        compress_count: int | None = None,
    ) -> Summary:
        """
        Create or get a Prometheus Summary metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.
            objectives (Optional[Dict[float, float]]): Summary quantile objectives.
            max_age_seconds (Optional[int]): Max age for summary observations.
            age_buckets (Optional[int]): Number of age buckets.
            compress_count (Optional[int]): Number of compressions.

        Returns:
            Summary: Prometheus Summary metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> summ = metrics.summary("request_duration_seconds", "Request duration", ["endpoint"])
            >>> summ.labels(endpoint="/api").observe(0.37)
        """
        labelnames = labelnames or []
        kwargs: dict[str, Any] = {}
        if objectives is not None:
            kwargs["objectives"] = objectives
        if max_age_seconds is not None:
            kwargs["max_age_seconds"] = max_age_seconds
        if age_buckets is not None:
            kwargs["age_buckets"] = age_buckets
        if compress_count is not None:
            kwargs["compress_count"] = compress_count
        key = self._metric_key("summary", name, labelnames, **kwargs)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Summary(
            f"{self.service_name}_{name}",
            documentation,
            labelnames=labelnames,
            **kwargs,
        )
        self._metrics[key] = metric
        return metric

    def info(
        self,
        name: str,
        documentation: str,
        labelnames: Sequence[str] | None = None,
        **kwargs: Any,
    ) -> Info:
        """
        Create or get a Prometheus Info metric.

        Args:
            name (str): Metric name (without service prefix).
            documentation (str): Metric description.
            labelnames (Optional[Sequence[str]]): List of label names.

        Returns:
            Info: Prometheus Info metric instance.

        Examples:
            >>> metrics = MetricFactory("my_service")
            >>> info = metrics.info("build_info", "Build and version info")
            >>> info.info({"version": "1.0.0", "build": "abc123"})
        """
        labelnames = labelnames or []
        key = self._metric_key("info", name, labelnames)
        if key in self._metrics:
            return self._metrics[key]  # type: ignore
        metric = Info(
            f"{self.service_name}_{name}", documentation, labelnames=labelnames
        )
        self._metrics[key] = metric
        return metric
