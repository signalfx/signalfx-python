#!/usr/bin/env python

# Copyright (C) 2017-2019 SignalFx, Inc. All rights reserved.
# Copyright (C) 2020 Splunk, Inc. All rights reserved.
#
# An example of how to accumulate the output of a SignalFlow computation and
# convert it into a Pandas DataFrame for analysis.

import argparse
import os
import pandas
import sys
import time

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..'))
import signalfx  # noqa
from signalfx.signalflow import messages  # noqa


def get_data_frame(client, program, start, stop, resolution=None):
    """Executes the given program across the given time range (expressed in
    millisecond timestamps since Epoch), and returns a Pandas DataFrame
    containing the results, indexed by output timestamp.

    If the program contains multiple publish() calls, their outputs are merged
    into the returned DataFrame."""
    data = {}
    metadata = {}

    c = client.execute(program, start=start, stop=stop, resolution=resolution)
    for msg in c.stream():
        if isinstance(msg, messages.DataMessage):
            if msg.logical_timestamp_ms in data:
                data[msg.logical_timestamp_ms].update(msg.data)
            else:
                data[msg.logical_timestamp_ms] = msg.data
        elif isinstance(msg, messages.MetadataMessage):
            metadata[msg.tsid] = msg.properties

    df = pandas.DataFrame.from_dict(data, orient='index')
    df.metadata = metadata
    return df


if __name__ == '__main__':
    now = int(time.time()) * 1000

    parser = argparse.ArgumentParser(
        description='SignalFx SignalFlow output to Pandas DataFrame')
    parser.add_argument('--stream-endpoint',
                        help='SignalFx SignalFlow stream API endpoint',
                        default='https://stream.signalfx.com')
    parser.add_argument('-a', '--start', type=int,
                        help='Start timestamp (in milliseconds)',
                        default=now - 15 * 60 * 1000)
    parser.add_argument('-o', '--stop', type=int,
                        help='End timestamp (in milliseconds)',
                        default=now - 5 * 60 * 1000)
    parser.add_argument('-r', '--resolution', type=int,
                        help='Minimum desired resolution')
    parser.add_argument('token', help='Your SignalFx API access token')
    parser.add_argument('program', help='SignalFlow program to execute')
    options = parser.parse_args()
    client = signalfx.SignalFx(stream_endpoint=options.stream_endpoint)
    flow = client.signalflow(options.token)
    print(get_data_frame(flow, options.program, options.start,
                         options.stop, options.resolution))
