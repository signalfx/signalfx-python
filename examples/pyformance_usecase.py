#!/usr/bin/env python

# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import argparse
import os
import logging
import sys
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))

# import the signalfx pyformance library
import signalfx.pyformance  as pyf # noqa


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='SignalFx metrics reporting demo')
    parser.add_argument('token', help='Your SignalFx API access token')
    options = parser.parse_args()

    # @pyf.count_calls counts the number of times callme is invoked
    # and adds the metric to the global pyformance registry
    @pyf.count_calls
    def callme():
        logging.info('Called me!')
        # pyf.gauge() adds a gauge to the global pyformance registry
        pyf.gauge('demo.time').set_value(time.time())

    # @pyf.count_calls_with_dims counts the number of times
    # callme_with_dims is invoked.  The dimension
    # ("dimension_key"="dimension_value") is included on the metric
    @pyf.count_calls_with_dims(dimension_key="dimension_value")
    def callme_with_dims():
        logging.info('Called me with dimensions!')
        # pyf.gauge() adds a gauge to the global pyformance registry
        # and accepts dimensions as keyword arguments
        pyf.gauge('demo.time2',
                  dimension_key="dimension_value").set_value(time.time())

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    # the signalfx reporter uses the pyformance global_registry by default
    sfx = pyf.SignalFxReporter(options.token)
    sfx.start()

    # a custom registry can be created with SignalFx Pyformance MetricsRegistry
    custom_registry = pyf.MetricsRegistry()

    # a custom registry can be set as the global registry using
    # pyf.set_global_registry(custom_registry)

    # the new registry must be passed to a new SignalFx Pyformance Reporter
    custom_sfx = pyf.SignalFxReporter(options.token, registry=custom_registry)
    custom_sfx.start()

    # @ style decorators only work with the global registry
    def custom_callme():
        logging.info('Called me!')
        # metrics may be registered with the new registry
        custom_registry.gauge('demo.time.custom').set_value(time.time())

    def custom_callme_with_dims():
        logging.info('Called me with dimensions!')
        # pass dimensions as keyword arguments in the metric function
        # calls in the signalfx pyformance library
        custom_registry.gauge(
            'demo.time2.custom',
            dimension_key="dimension_value").set_value(time.time())

    pyf.gauge('demo.pid').set_value(os.getpid())

    try:
        while True:
            callme()
            callme_with_dims()
            custom_callme()
            custom_callme_with_dims()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    sfx.stop()
    custom_sfx.stop()
