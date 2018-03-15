#!/usr/bin/env python

# Copyright (C) 2017 SignalFx, Inc. All rights reserved.

import unittest
import signalfx.signalflow.ws
import struct


class WebSocketTransportTest(unittest.TestCase):

    def test_decode_binary_format_v1(self):
        data = struct.pack(
                '!BBxx16sqiBqqBqd',
                1, 5, b'foo', 1234,
                2, 1, 10, 42, 2, 11, 3.14)
        ws = signalfx.signalflow.ws.WebSocketTransport('token')
        decoded = ws.decode_binary_message(data)
        self.assertEqual(decoded, {
            'type': 'data',
            'channel': u'foo',
            'logicalTimestampMs': 1234,
            'maxDelayMs': None,
            'data': [{
                'tsId': u'AAAAAAAAAAo',
                'value': 42,
            }, {
                'tsId': u'AAAAAAAAAAs',
                'value': 3.14,
            }]
        })

    def test_decode_binary_format_v3(self):
        data = struct.pack(
                '!BBxx16sqqiBqqBqdBqqBqq',
                3, 5, b'foo', 1234, 4321,
                4, 1, 10, 42, 2, 11, 3.14, 0, 12, 0, 3, 13, 42)
        ws = signalfx.signalflow.ws.WebSocketTransport('token')
        decoded = ws.decode_binary_message(data)
        self.assertEqual(decoded, {
            'type': 'data',
            'channel': u'foo',
            'logicalTimestampMs': 1234,
            'maxDelayMs': 4321,
            'data': [{
                'tsId': u'AAAAAAAAAAo',
                'value': 42,
            }, {
                'tsId': u'AAAAAAAAAAs',
                'value': 3.14,
            }, {
                'tsId': u'AAAAAAAAAAw',
                'value': None,
            }, {
                'tsId': u'AAAAAAAAAA0',
                'value': 42
            }]
        })


if __name__ == '__main__':
    unittest.main()
