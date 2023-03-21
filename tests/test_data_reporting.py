#!/usr/bin/env python

# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import logging
import os
import sys
import signalfx
import time
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--token", choices=["valid", "invalid"], default="valid", type=str, help="Provider Name")
args = parser.parse_args()

if args.token == "invalid":
    MY_TOKEN = "123-12345678-123456789"
else:
    MY_TOKEN = os.environ['SIGNALFX_API_TOKEN']
sfx = signalfx.SignalFx().ingest(MY_TOKEN)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Basic Usage
sfx.send(
        gauges=[
            {'metric': 'myfunc.time',
             'value': 532,
             'timestamp': time.time()*1000}
        ],
        counters=[
            {'metric': 'myfunc.calls',
             'value': 42,
             'timestamp': time.time()*1000}
        ],
        cumulative_counters=[
            {'metric': 'myfunc.calls_cumulative',
             'value': 10,
             'timestamp': time.time()*1000}
        ])

# Multi-dimensional data
sfx.send(
        gauges=[
            {
                'metric': 'myfunc.time',
                'value': 532,
                'timestamp': time.time()*1000,
                'dimensions': {'host': 'server1', 'host_ip': '1.2.3.4'}
            }
        ])

# Sending events
sfx.send_event(
        event_type='deployments_test',
        category='USER_DEFINED',
        dimensions={
            'host': 'myhost',
            'service': 'myservice',
            'instance': 'myinstance'},
        properties={
            'version': '2015.04.29-01'},
        timestamp=time.time()*1000)

# After all datapoints have been sent, flush any remaining messages
# in the send queue and terminate all connections
sfx.stop()
