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
                 registry=None, reporting_interval=1):
        reporter.Reporter.__init__(self, registry=registry,
                                   reporting_interval=reporting_interval)
        self._sfx = signalfx.SignalFx(api_token, ingest_endpoint=url)

    def report_now(self, registry=None, timestamp=None):
        registry = registry or self.registry
        metrics = registry.dump_metrics()

        gauges = []
        counters = []

        for metric, details in metrics.items():
            for submetric, value in details.items():
                info = {'name': metric, 'value': value}
                if submetric == 'count':
                    counters.append(info)
                else:
                    if submetric != 'value':
                        info['name'] = '{}.{}'.format(info['name'], submetric)
                    gauges.append(info)

        r = self._sfx.send(gauges, counters)
        if r is None:
            return
        if not r:
            try:
                error = r.json()['message']
            except:
                error = '{} {}'.format(r.status_code, r.text)
            logging.error('Error sending metrics to SignalFx: %s', error)
