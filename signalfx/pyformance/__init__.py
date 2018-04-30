#!/usr/bin/env python

# Copyright (C) 2014 SignalFuse, Inc. All rights reserved.
# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

import functools
from pyformance.registry import global_registry, get_qualname
from pyformance.reporters import reporter
import signalfx
import logging


class MetricMetadata(object):
    """Metric dimensions metadata repository.

    This class mediates the registration of metrics with additional dimensions
    and registers the metrics in the Pyformance registry using a unique
    composite name, while recording the mapping from composite name to the
    original metric name and dimensions.

    It then makes this information available to the SignalFxReporter so metrics
    can be reported with the appropriate metric and dimensions.
    """

    def __init__(self, registry=None):
        self._metadata = {}
        self._registry = registry or global_registry()

    def get_metadata(self, key):
        dimensions = self._metadata.get(key)
        return dimensions or {}

    def register(self, registration_fn, key, gauge=None, **kwargs):
        dimensions = dict((k, str(v)) for k, v in kwargs.items())
        composite_key = self._composite_name(key, dimensions)
        self._metadata[composite_key] = {
            'metric': key,
            'dimensions': dimensions
        }
        return registration_fn(composite_key)

    def _composite_name(self, metric_name, dimensions=None):
        composite = []
        if dimensions:
            for key in sorted(dimensions.keys()):
                composite.append('{}={}'.format(key, dimensions[key]))
        composite.append(metric_name)
        return '.'.join(composite)

    def clear(self):
        """clears the registered metadata"""
        self._metdata.clear()

    def counter(self, key, **kwargs):
        """adds counter with dimensions to the registry"""
        return self.register(self._registry.counter, key, **kwargs)

    def gauge(self, key, gauge=None, default=float("nan"), **kwargs):
        """adds gauge with dimensions to the registry"""
        return self.register(self._registry.gauge, key, gauge=gauge,
                             default=default, **kwargs)

    def timer(self, key, **kwargs):
        """adds timer with dimensions to the registry"""
        return self.register(self._registry.timer, key, **kwargs)

    def histogram(self, key, **kwargs):
        """adds histogram with dimensions to the registry"""
        return self.register(self._registry.histogram, key, **kwargs)

    def meter(self, key, **kwargs):
        """adds meter with dimensions to the registry"""
        return self.register(self._registry.meter, key, **kwargs)

    def count_calls(self, **dims):
        """decorator to track the number of times a function is called."""
        def counter_wrapper(fn):
            @functools.wraps(fn)
            def fn_wrapper(*args, **kwargs):
                self.counter("%s_calls" % get_qualname(fn), **dims).inc()
                return fn(*args, **kwargs)
            return fn_wrapper
        return counter_wrapper

    def meter_calls(self, **dims):
        """decorator to track the rate at which a function is called."""
        def meter_wrapper(fn):
            @functools.wraps(fn)
            def fn_wrapper(*args, **kwargs):
                self. meter("%s_calls" % get_qualname(fn), **dims).mark()
                return fn(*args, **kwargs)
            return fn_wrapper
        return meter_wrapper

    def hist_calls(self, **dims):
        """decorator to check the distribution of return values of a
        function.
        """
        def hist_wrapper(fn):
            @functools.wraps(fn)
            def fn_wrapper(*args, **kwargs):
                _histogram = self.histogram(
                    "%s_calls" % get_qualname(fn), **dims)
                rtn = fn(*args, **kwargs)
                if type(rtn) in (int, float):
                    _histogram.update(rtn)
                return rtn
            return fn_wrapper
        return hist_wrapper

    def time_calls(self, **dims):
        """decorator to time the execution of the function."""
        def time_wrapper(fn):
            @functools.wraps(fn)
            def fn_wrapper(*args, **kwargs):
                _timer = self.timer("%s_calls" % get_qualname(fn), **dims)
                with _timer.time(fn=get_qualname(fn)):
                    return fn(*args, **kwargs)
            return fn_wrapper
        return time_wrapper


_global_metadata = MetricMetadata()


def global_metadata():
    """returns the global metadata"""
    return _global_metadata


def set_global_metadata(metadata):
    """sets the global metadata obj"""
    global _global_metadata
    _global_metadata = metadata


def counter(key, **kwargs):
    """adds counter with dimensions to the global pyformance registry"""
    return global_metadata().counter(key, **kwargs)


def gauge(key, gauge=None, default=float("nan"), **kwargs):
    """adds gauge with dimensions to the global pyformance registry"""
    return global_metadata().gauge(key, gauge=gauge, default=default, **kwargs)


def timer(key, **kwargs):
    """adds timer with dimensions to the global pyformance registry"""
    return global_metadata().timer(key, **kwargs)


def histogram(key, **kwargs):
    """adds histogram with dimensions to the global pyformance registry"""
    return global_metadata().histogram(key, **kwargs)


def meter(key, **kwargs):
    """adds meter with dimensions to the global pyformance registry"""
    return global_metadata().meter(key, **kwargs)


def clear():
    """clears the global metadata store"""
    return global_metadata().clear()


def count_calls(**dims):
    """decorator to track the number of times a function is called."""
    return global_metadata().count_calls(**dims)


def meter_calls(**dims):
    """decorator to track the rate at which a function is called."""
    return global_metadata().meter_calls(**dims)


def hist_calls(**dims):
    """decorator to check the distribution of return values of a function."""
    return global_metadata().hist_calls(**dims)


def time_calls(**dims):
    """decorator to time the execution of the function."""
    return global_metadata().time_calls(**dims)


class SignalFxReporter(reporter.Reporter):
    """A pyformance reporter that sends data to SignalFx.

    To use, you will need a SignalFx account (www.signalfx.com) and your API
    access token, and then simply get an instance of SignalFxReporter and
    start() it. You can optionally pass-in the pyformance metric registry that
    you want to be reporting; if none is given, the global registry (as defined
    by pyformance) will be used.
    """

    def __init__(
            self, token, ingest_endpoint=signalfx.DEFAULT_INGEST_ENDPOINT,
            registry=None, reporting_interval=1, default_dimensions=None,
            metadata=None):
        if default_dimensions is not None and not isinstance(
                default_dimensions, dict):
            raise TypeError('The default_dimensions argument must be a '
                            'dict of string keys to string values.')

        super(SignalFxReporter, self).__init__(
            registry=registry,
            reporting_interval=reporting_interval)

        self._default_dimensions = default_dimensions
        self._metadata = metadata or global_metadata()

        self._sfx = (signalfx.SignalFx(ingest_endpoint=ingest_endpoint)
                     .ingest(token))

    def report_now(self, registry=None, timestamp=None):
        registry = registry or self.registry
        metrics = registry.dump_metrics()

        timestamp = timestamp or int(self.clock.time())
        sf_timestamp = timestamp * 10 ** 3

        cumulative_counters = []
        gauges = []

        for metric, details in metrics.items():
            for submetric, value in details.items():
                info = {
                    'metric': metric,
                    'value': value,
                    'timestamp': sf_timestamp
                }

                metadata = self._metadata.get_metadata(metric)
                if metadata:
                    info['metric'] = metadata['metric']
                    info['dimensions'] = dict(metadata['dimensions'])

                if self._default_dimensions:
                    info['dimensions'].update(self._default_dimensions)

                if submetric == 'count':
                    cumulative_counters.append(info)
                else:
                    if submetric != 'value':
                        info['metric'] += '.{}'.format(submetric)
                    gauges.append(info)

        logging.debug('Sending counters: %s and gauges: %s',
                      cumulative_counters, gauges)
        self._sfx.send(cumulative_counters=cumulative_counters, gauges=gauges)

    def stop(self):
        super(SignalFxReporter, self).stop()
        self._sfx.stop()
