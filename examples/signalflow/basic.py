#!/usr/bin/env python

# Copyright (C) 2017 SignalFx, Inc. All rights reserved.
#
# A simple example showing how to execute a SignalFx SignalFlow computation
# from Python and dump its data, metadata and event output to the console.

import argparse
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import signalfx  # noqa
from signalfx.signalflow import messages  # noqa


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='SignalFx SignalFlow streaming analytics demo')
    parser.add_argument('--stream-endpoint',
                        help='SignalFx SignalFlow stream API endpoint',
                        default='https://stream.signalfx.com')
    parser.add_argument('token', help='Your SignalFx API access token')
    parser.add_argument('program', help='SignalFlow program to execute')
    options = parser.parse_args()
    client = signalfx.SignalFx(stream_endpoint=options.stream_endpoint)
    flow = client.signalflow(options.token)

    try:
        # Execute the computation and iterate over the message stream
        print('Requesting computation: {0}'.format(options.program))
        c = flow.execute(options.program)
        print('Waiting for data...')
        for msg in c.stream():
            if isinstance(msg, messages.DataMessage):
                print('\033[34;1m{0}\033[;0m @{1}: {2}'.format(
                    'data', msg.logical_timestamp_ms,
                    ', '.join(['\033[;1m{0}\033[;0m: {1}'.format(k, v)
                               for k, v in msg.data.items()])))
            elif isinstance(msg, messages.EventMessage):
                print('\033[35;1m{0}\033[34;1m@\033[;0m @{1}: {2}'.format(
                    'event', msg.timestamp_ms,
                    ', '.join(['\033[;1m{0}\033[;0m: {1}'.format(k, v)
                               for k, v in msg.properties.items()])))
            elif isinstance(msg, messages.MetadataMessage):
                print('\033[32;1m{0}\033[;0m for \033[;1m{1}\033[;0m:\n  {2}'
                      .format(
                          'metadata', msg.tsid,
                          '\n  '.join(['\033[;1m{0}\033[;0m: {1}'
                                       .format(k, v)
                                       for k, v in msg.properties.items()])))
    except KeyboardInterrupt:
        print(' Detaching from computation...')
    finally:
        flow.close()
    print('Done.')
