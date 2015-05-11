#!/usr/bin/env python

# Copyright (C) 2014 SignalFuse, Inc.
# Copyright (C) 2015 SignalFx, Inc.

from pyformance.reporters import reporter
import signalfx
import logging


class SignalFxReporter(reporter.Reporter):
    """A pyformance reporter that sends data to SignalFx.

    To use, you will need a SignalFx account (www.signalfx.com) and your API
    access token, and then simply get an instance of SignalFxReporter and
    start() it. You can optionally pass-in the pyformance metric registry that
    you want to be reporting; if none is given, the global registry (as defined
    by pyformance) will be used.
    """

    def __init__(self, api_token, url=signalfx.DEFAULT_INGEST_ENDPOINT_URL,
                 registry=None, reporting_interval=1,
                 default_dimensions=None):
        reporter.Reporter.__init__(self, registry=registry,
                                   reporting_interval=reporting_interval)
        self.default_dimensions = default_dimensions
        if default_dimensions is None:
            self.default_dimensions = {}
        self._sfx = signalfx.SignalFx(api_token, ingest_endpoint=url)

    def report_now(self, registry=None, timestamp=None):
        registry = registry or self.registry
        metrics = registry.dump_metrics()

        timestamp = timestamp or int(self.clock.time())
        sf_timestamp = timestamp * 10**3

        cumulative_counters = []
        gauges = []

        for metric, details in metrics.items():
            for submetric, value in details.items():
                info = {
                    'metric': metric,
                    'value': value,
                    timestamp: sf_timestamp
                }
                if len(self.default_dimensions) > 0:
                    # TODO(wt): Plumbing in custom dimensions at some point will
                    # require copying the default dimensions instead of using
                    # them directly.
                    info['dimensions'] = self.default_dimensions
                if submetric == 'count':
                    cumulative_counters.append(info)
                else:
                    if submetric != 'value':
                        info['metric'] += '.{}'.format(submetric)
                    gauges.append(info)

        r = self._sfx.send(
            cumulative_counters=cumulative_counters, gauges=gauges)
        if r is None:
            return
        if not r:
            try:
                error = r.json()['message']
            except:
                error = '{} {}'.format(r.status_code, r.text)
            logging.error('Error sending metrics to SignalFx: %s', error)
