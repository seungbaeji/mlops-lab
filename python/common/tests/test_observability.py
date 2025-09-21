import logging

from mrml_common.observability import (
    JSONFormatter,
    LogfmtFormatter,
    MetricFactory,
    get_tracer,
    span_context,
)


def test_counter_metric_creation_and_increment():
    metrics = MetricFactory("test_service")
    counter = metrics.counter("test_counter", "A test counter", ["label"])
    c = counter.labels(label="foo")
    before = c._value.get()
    c.inc()
    after = c._value.get()
    assert after == before + 1


def test_gauge_metric_creation_and_set():
    metrics = MetricFactory("test_service")
    gauge = metrics.gauge("test_gauge", "A test gauge", ["label"])
    g = gauge.labels(label="bar")
    g.set(42)
    assert g._value.get() == 42


def test_histogram_metric_observe():
    metrics = MetricFactory("test_service")
    hist = metrics.histogram(
        "test_hist", "A test histogram", ["label"], buckets=[1, 2, 3]
    )
    h = hist.labels(label="baz")
    h.observe(2.5)
    # Use collect() to get the sum sample
    samples = list(hist.collect())[0].samples
    sum_sample = [s for s in samples if s.name.endswith("_sum")][0]
    assert sum_sample.value > 0


def test_summary_metric_observe():
    metrics = MetricFactory("test_service")
    summ = metrics.summary("test_summary", "A test summary", ["label"])
    s = summ.labels(label="qux")
    s.observe(1.23)
    samples = list(summ.collect())[0].samples
    sum_sample = [s for s in samples if s.name.endswith("_sum")][0]
    assert sum_sample.value > 0


def test_info_metric_set():
    metrics = MetricFactory("test_service")
    info = metrics.info("test_info", "A test info")
    info.info({"version": "1.0.0"})
    # Info metrics do not have a numeric value, but should not raise


def test_get_tracer_returns_tracer():
    tracer = get_tracer("test_service")
    assert hasattr(tracer, "start_as_current_span")


def test_span_context_returns_context_manager():
    tracer = get_tracer("test_service")
    ctx_mgr = span_context(tracer, "test_span")
    # Should be usable as a context manager
    assert hasattr(ctx_mgr, "__enter__") and hasattr(ctx_mgr, "__exit__")


def test_json_formatter_output():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    formatter = JSONFormatter()
    output = formatter.format(record)
    assert '"message": "hello"' in output
    assert '"level": "INFO"' in output


def test_logfmt_formatter_output():
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    formatter = LogfmtFormatter()
    output = formatter.format(record)
    assert "message=hello" in output
    assert "level=INFO" in output
