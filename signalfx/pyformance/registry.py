# Copyright (C) 2018-2019 SignalFx, Inc. All rights reserved.
# Copyright (C) 2020 Splunk, Inc. All rights reserved.

import functools
from .metadata import MetricMetadata
import pyformance.registry
import re
import time
from pyformance.registry import (clear, count_calls, dump_metrics,  # noqa
                                 global_registry, meter_calls,
                                 set_global_registry, time_calls)


class MetricsRegistry(pyformance.registry.MetricsRegistry):
    """An extension of the pyformance MetricsRegistry
    which accepts and manages dimensional data to emit to SignalFx
    """
    def __init__(self, clock=time):
        self.metadata = MetricMetadata()
        super(MetricsRegistry, self).__init__(clock=clock)

    def add(self, key, metric, **dims):
        """Adds custom metric instances to the registry with dimensions
        which are not created with their constructors default arguments
        """
        return super(MetricsRegistry, self).add(
            self.metadata.register(key, **dims), metric)

    def counter(self, key, **dims):
        """Adds counter with dimensions to the registry"""
        return super(MetricsRegistry, self).counter(
            self.metadata.register(key, **dims))

    def histogram(self, key, **dims):
        """Adds histogram with dimensions to the registry"""
        return super(MetricsRegistry, self).histogram(
            self.metadata.register(key, **dims))

    def gauge(self, key, gauge=None, default=float("nan"), **dims):
        """Adds gauge with dimensions to the registry"""
        return super(MetricsRegistry, self).gauge(
            self.metadata.register(key, **dims), gauge=gauge, default=default)

    def meter(self, key, **dims):
        """Adds meter with dimensions to the registry"""
        return super(MetricsRegistry, self).meter(
            self.metadata.register(key, **dims))

    def timer(self, key, **dims):
        """Adds timer with dimensions to the registry"""
        return super(MetricsRegistry, self).timer(
            self.metadata.register(key, **dims))

    def clear(self): # noqa
        """Clears the registered metrics and metadata"""
        self.metadata.clear()
        super(MetricsRegistry, self).clear()


# set global registry on import to the SignalFx MetricsRegistry
set_global_registry(MetricsRegistry())


class RegexRegistry(MetricsRegistry):
    """
    An extension of the pyformance RegexRegistry
    which accepts and manages dimensional data to emit to SignalFx.
    The RegexRegistry captures all api calls matching the specified
    regex patterns and groups them together.  This is useful to avoid
    defining a metric for each method of a REST API
    """
    def __init__(self, pattern=None, clock=time):
        super(RegexRegistry, self).__init__(clock)
        if pattern is not None:
            self.pattern = re.compile(pattern)
        else:
            self.pattern = re.compile('^$')

    def _get_key(self, key):
        matches = self.pattern.finditer(key)
        key = '/'.join((v for match in matches for v in match.groups() if v))
        return key

    def timer(self, key, **dims):
        """Adds timer with dimensions to the registry"""
        return super(RegexRegistry, self).timer(self._get_key(key), **dims)

    def histogram(self, key, **dims):
        """Adds histogram with dimensions to the registry"""
        return super(RegexRegistry, self).histogram(self._get_key(key), **dims)

    def counter(self, key, **dims):
        """Adds counter with dimensions to the registry"""
        return super(RegexRegistry, self).counter(self._get_key(key), **dims)

    def gauge(self, key, gauge=None, default=float("nan"), **dims):
        """Adds gauge with dimensions to the registry"""
        return super(RegexRegistry, self).gauge(
            self._get_key(key), gauge=gauge, default=default, **dims)

    def meter(self, key, **dims):
        """Adds meter with dimensions to the registry"""
        return super(RegexRegistry, self).meter(self._get_key(key), **dims)


def counter(key, **dims):
    """Adds counter with dimensions to the global pyformance registry"""
    return global_registry().counter(key, **dims)


def histogram(key, **dims):
    """Adds histogram with dimensions to the global pyformance registry"""
    return global_registry().histogram(key, **dims)


def meter(key, **dims):
    """Adds meter with dimensions to the global pyformance registry"""
    return global_registry().meter(key, **dims)


def timer(key, **dims):
    """Adds timer with dimensions to the global pyformance registry"""
    return global_registry().timer(key, **dims)


def gauge(key, gauge=None, default=float("nan"), **dims):
    """Adds gauge with dimensions to the global pyformance registry"""
    return global_registry().gauge(key, gauge=gauge, default=default, **dims)


def count_calls_with_dims(**dims):
    """Decorator to track the number of times a function is called
    with with dimensions.
    """
    def counter_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            counter("%s_calls" %
                    pyformance.registry.get_qualname(fn), **dims).inc()
            return fn(*args, **kwargs)
        return fn_wrapper
    return counter_wrapper


def meter_calls_with_dims(**dims):
    """Decorator to track the rate at which a function is called
    with dimensions.
    """
    def meter_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            meter("%s_calls" %
                  pyformance.registry.get_qualname(fn), **dims).mark()
            return fn(*args, **kwargs)
        return fn_wrapper
    return meter_wrapper


# TODO: raise bug with pyformance on their implementation of hist_calls
# _histogram does not have an update method so use add instead
def hist_calls(fn):
    """
    Decorator to check the distribution of return values of a function.
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        _histogram = histogram(
            "%s_calls" % pyformance.registry.get_qualname(fn))
        rtn = fn(*args, **kwargs)
        if type(rtn) in (int, float):
            _histogram.add(rtn)
        return rtn
    return wrapper


def hist_calls_with_dims(**dims):
    """Decorator to check the distribution of return values of a
    function with dimensions.
    """
    def hist_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            _histogram = histogram(
                "%s_calls" % pyformance.registry.get_qualname(fn), **dims)
            rtn = fn(*args, **kwargs)
            if type(rtn) in (int, float):
                _histogram.add(rtn)
            return rtn
        return fn_wrapper
    return hist_wrapper


def time_calls_with_dims(**dims):
    """Decorator to time the execution of the function with dimensions."""
    def time_wrapper(fn):
        @functools.wraps(fn)
        def fn_wrapper(*args, **kwargs):
            _timer = timer("%s_calls" %
                           pyformance.registry.get_qualname(fn), **dims)
            with _timer.time(fn=pyformance.registry.get_qualname(fn)):
                return fn(*args, **kwargs)
        return fn_wrapper
    return time_wrapper
