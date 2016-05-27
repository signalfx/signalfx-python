#!/usr/bin/env python

# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import argparse
import os
import logging
import sys
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))
import signalfx  # noqa


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='SignalFx metrics reporting demo')
    parser.add_argument('token', help='Your SignalFx API access token')
    options = parser.parse_args()
    client = signalfx.SignalFx()
    ingest = client.Ingest(options.token)
    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

    try:
        i = 0
        while True:
            ingest.send(gauges=[{
                'metric': 'test.cpu',
                'value': i % 10}],
                counters=[{
                    'metric': 'cpu_cnt',
                    'value': i % 2}])
            i += 1
            if i % 10 == 0:  # Factoring for reduced activity for events
                version = '{date}-{version}'.format(
                    date=time.strftime('%Y-%m-%d'), version=i)
                ingest.send_event(event_type='deployments',
                                  category='USER_DEFINED',
                                  dimensions={
                                      'host': 'myhost',
                                      'service': 'myservice',
                                      'instance': 'myinstance'},
                                  properties={'version': version},
                                  timestamp=time.time() * 1000)
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
