#!/usr/bin/env python

# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import argparse
import os
import logging
import pyformance as pyf
import sys
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))
import signalfx.pyformance  # noqa


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='SignalFx metrics reporting demo')
    parser.add_argument('token', help='Your SignalFx API access token')
    options = parser.parse_args()

    @pyf.count_calls
    def callme():
        logging.info('Called me!')
        pyf.gauge('demo.time').set_value(time.time())

    # the signalfx pyformance module has decorators and functions for
    # reporting metrics with custom dimensions
    @signalfx.pyformance.count_calls(dimension1="dimension2")
    def callme_with_dimensions():
        logging.info('Called me with dimensions!')
        # dimensions can be passed as keyword arguments in the
        # metric function call from the signalfx pyformance library
        signalfx.pyformance.gauge('demo.time2', dimension1="dimension2"
                                  ).set_value(time.time())

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    # the signalfx reporter uses the global_metadata and
    # global_registry by default
    sfx = signalfx.pyformance.SignalFxReporter(options.token)
    sfx.start()

    # if you wish to use a custom registry
    # create the custom registry using pyformance
    custom_registry = pyf.MetricsRegistry()
    # create the custom MetricMetadata from signalfx and pass it
    # the new registry
    custom_registry_metadata = signalfx.pyformance.MetricMetadata(
        custom_registry)
    # pass both the registry and metadata into a new SignalFxReporter
    custom_sfx = signalfx.pyformance.SignalFxReporter(
        options.token, registry=custom_registry,
        metadata=custom_registry_metadata)

    # use the functions and decorators on the MetricMetadata to emit
    # metrics with dimensions
    @custom_registry_metadata.count_calls()
    def custom_callme():
        logging.info('Called me!')
        pyf.gauge('demo.custom.time').set_value(time.time())

    @custom_registry_metadata.count_calls(hello="world")
    def custom_callme_with_dimensions():
        logging.info('Called me with dimensions!')
        # pass dimensions as keyword arguments in the metric function
        # calls in the signalfx pyformance library
        signalfx.pyformance.gauge('demo.custom.time2',
                                  hello="world").set_value(time.time())

    pyf.gauge('demo.pid').set_value(os.getpid())

    try:
        while True:
            callme()
            callme_with_dimensions()
            custom_callme()
            custom_callme_with_dimensions()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    sfx.stop()
