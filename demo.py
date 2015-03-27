#!/usr/bin/env python

import argparse
import logging
import pyformance as pyf
import os
import signalfx.pyformance
import sys
import time

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
    sf = signalfx.pyformance.SignalFxReporter(options.token)
    sf.start()

    pyf.gauge('demo.pid').set_value(os.getpid())

    try:
        while True:
            callme()
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
