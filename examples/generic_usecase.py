#!/usr/bin/env python

import os
import sys
sys.path.append(os.path.realpath('..'))

import argparse
import logging
import signalfx
import time


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='SignalFx metrics reporting demo')
    parser.add_argument('token', help='Your SignalFx API access token')
    options = parser.parse_args()
    client = signalfx.SignalFx(options.token)
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    try:
        i = 0
        while True:
            client.send(gauges=[{
                                'metric': 'test.cpu',
                                'value': i % 10}],
                        counters=[{
                                  'metric': 'cpu_cnt',
                                  'value': i % 2}])
            i += 1
            if i % 10 == 0:  # Factoring for reduced activity for events
                version = '{date}-{version}'.format(
                    date=time.strftime('%Y-%m-%d'), version=i)
                client.send_event(event_type='deployments',
                                  dimensions={
                                      'host': 'myhost',
                                      'service': 'myservice',
                                      'instance': 'myinstance'},
                                  properties={'version': version})
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
