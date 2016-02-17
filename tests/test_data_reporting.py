import logging
import os
import signalfx
import sys
import time

MY_TOKEN = os.environ['SIGNALFX_API_TOKEN']
sfx = signalfx.SignalFx(MY_TOKEN)
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
        event_type='deployments',
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
