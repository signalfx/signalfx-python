#!/usr/bin/env python

# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

"""
"Live" tests for SignalFx Python client library.

to run this script, use "python live_tests.py --token YOUR_TOKEN"

optional command line arguments:
  --metric_name FAKE_METRIC, --tag_name FAKE_TAG, --key FAKE KEY,
  --value FAKE_VALUE

"""

import time
import sys
import os
import argparse
import requests

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))
import signalfx  # noqa


parser = argparse.ArgumentParser()
parser.add_argument('--token')
parser.add_argument('--metric_name')
parser.add_argument('--tag_name')
parser.add_argument('--key')
parser.add_argument('--value')
args = parser.parse_args()

if not args.token:
    args.token = os.environ['SIGNALFX_API_TOKEN']
if not args.metric_name:
    args.metric_name = 'fake..metric_to_"test'
if not args.tag_name:
    args.tag_name = '"fake_tag_name"~'
if not args.key:
    args.key = 'fake_key"%'
if not args.value:
    args.value = 'fake_value'

FAKE_METRIC_NAME, FAKE_TAG, FAKE_KEY, FAKE_VALUE = \
    args.metric_name, args.tag_name, args.key, args.value

TOKEN = args.token
gT, sT, dT, uT = 'get_tag', 'search_tags', 'delete_tag', 'update_tag'
sD, uD, gD = 'search_dimensions', 'update_dimension', 'get_dimension'

sfx = signalfx.SignalFx().rest(TOKEN)
CLIENT_NAME = 'sfx'


def test_func(client_name, func_name, sleep_time=5, msg='is being tested!',
              func_args=None, **kwargs):
    return_value = None
    if func_name in dir(eval(client_name)):
        try:
            func = eval(client_name + '.' + func_name)
            return_value = func(*func_args, **kwargs)
            print('{} {} -> {}'.format(func_name, msg, return_value))
            time.sleep(sleep_time)
        except requests.exceptions.HTTPError as e:
            print('{} -! {}'.format(func_name, e))
    else:
        print('{} is not available'.format(func_name))
    return return_value


def apply_sequence(client_name, sequence, f_args, seq_msg=None, **kwargs):
    print('{} expected behavior is {}'.format(sequence, seq_msg))
    for item in sequence:
        test_func(client_name, item, func_args=f_args, **kwargs)


def main():
    apply_sequence(CLIENT_NAME, [gT, sT, dT, uT, gT, sT, dT, gT, sT, uT,
                                 gT, sT, dT], (FAKE_TAG,), timeout=15)
    test_func(CLIENT_NAME, sD, func_args=[FAKE_KEY], timeout=15)
    apply_sequence(CLIENT_NAME, [uD, gD], (FAKE_KEY, FAKE_VALUE), timeout=15)
    test_func(CLIENT_NAME, sD, func_args=[FAKE_VALUE], timeout=15)
    test_func(CLIENT_NAME, 'get_metric_by_name', func_args=[FAKE_METRIC_NAME],
              timeout=15)
    test_func(CLIENT_NAME, 'search_metrics', func_args=[FAKE_METRIC_NAME],
              timeout=15)
    test_func(CLIENT_NAME, 'update_metric_by_name',
              func_args=[FAKE_METRIC_NAME, 'gauge'], timeout=15)
    r = test_func(CLIENT_NAME, 'search_metric_time_series',
                  func_args=[FAKE_METRIC_NAME], timeout=15)
    if r:
        if len(r['results']) > 0:
            mts_id = r['results'][0]['id']
            test_func(CLIENT_NAME, 'get_metric_time_series',
                      func_args=[mts_id])

if __name__ == '__main__':
    main()
