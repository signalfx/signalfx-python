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

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
    sfx = signalfx.pyformance.SignalFxReporter(options.token)
    sfx.start()

    pyf.gauge('demo.pid').set_value(os.getpid())

    try:
        while True:
            callme()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass

    sfx.stop()
