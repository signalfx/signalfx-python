#!/usr/bin/env python

# Copyright (C) 2014 SignalFuse, Inc. All rights reserved.
# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

from pyformance.registry import global_registry
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

    def __init__(self):
        self._metadata = {}

    def get_metadata(self, key):
        dimensions = self._metadata.get(key)
        return dimensions or {}

    def register(self, registration_fn, key, **kwargs):
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


_global_metadata = MetricMetadata()


def global_metadata():
    return _global_metadata


def counter(key, **kwargs):
    return global_metadata().register(global_registry().counter, key, **kwargs)


def gauge(key, **kwargs):
    return global_metadata().register(global_registry().gauge, key, **kwargs)


def timer(key, **kwargs):
    return global_metadata().register(global_registry().timer, key, **kwargs)


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

        logging.debug('Sending counters: %s and gauges: %s', cumulative_counters, gauges)
        self._sfx.send(cumulative_counters=cumulative_counters, gauges=gauges)

    def stop(self):
        super(SignalFxReporter, self).stop()
        self._sfx.stop()
