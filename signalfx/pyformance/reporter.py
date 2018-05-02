# Copyright (C) 2018 SignalFx, Inc. All rights reserved.

import logging
from pyformance.reporters import reporter
import signalfx


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
            registry=None, reporting_interval=1, default_dimensions=None):
        if default_dimensions is not None and not isinstance(
                default_dimensions, dict):
            raise TypeError('The default_dimensions argument must be a '
                            'dict of string keys to string values.')

        super(SignalFxReporter, self).__init__(
            registry=registry,
            reporting_interval=reporting_interval)

        self._default_dimensions = default_dimensions

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

                metadata = registry.metadata.get_metadata(metric)
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
