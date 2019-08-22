#!/usr/bin/env python

# Copyright (C) 2017 SignalFx, Inc. All rights reserved.

from httmock import all_requests, urlmatch, HTTMock
import json
import unittest
from six.moves.urllib import parse
import signalfx.signalflow.ws
import struct

responses_map = {
    'GET_DETECTOR': {
        'path': '/v2/detector/abc123',
        'content': open('tests/fixtures/get_detector_abc123.json').read(),
        'status_code': 200,
        'method': 'GET',
    },
    'GET_DETECTOR_INCIDENTS': {
        'path': '/v2/detector/abc123/incidents',
        'content': '[]',
        'status_code': 200,
        'method': 'GET',
    },
    'GET_DETECTOR_EVENTS': {
        'path': '/v2/detector/abc123/events',
        'content': '[]',
        'status_code': 200,
        'method': 'GET',
    },
    'GET_INCIDENTS': {
        'path': '/v2/incident',
        'content': open('tests/fixtures/get_incidents.json').read(),
        'status_code': 200,
        'method': 'GET',
        'params': {
            'include_resolved': 'true',
            'offset': '0',
        }
    },
    'GET_INCIDENT': {
        'path': '/v2/incident/abc123',
        'content': open('tests/fixtures/get_incident_abc123.json').read(),
        'status_code': 200,
        'method': 'GET',
    },
    'CLEAR_INCIDENT': {
        'path': '/v2/incident/abc123/clear',
        'content': '',
        'status_code': 200,
        'method': 'PUT',
    }
}

# Generates a function that can be used with HTTMock to test the endpoint.
# It will validate the params, URL and Method, whilst returning a spec response.
def mock_maker(name):
    @all_requests
    def mock_responder(url, request):
        spec = responses_map.get(name)
        if spec is None:
            raise Exception("Unknown mock")

        if spec.get('path') != url.path or request.method != spec.get('method'):
            return {
                'content': 'Unknown URL' + url.path,
                'status_code': 400,
                }

        if spec.get('params') is not None:
            incoming_params = parse.parse_qs(url.query)
            for k, v in spec.get('params').items():
                param = incoming_params.get(k)
                if param is None or param[0] != v:
                    return {
                        'content': 'Missing or incorrection query param: ' + k,
                        'status_code': 400
                    }

        return {
            'content': spec.get('content'),
            'status_code': spec.get('status_code'),
        }
    return mock_responder

class RESTTest(unittest.TestCase):

    def test_get_detector(self):
        name = 'GET_DETECTOR'
        with HTTMock(mock_maker(name)):
            with signalfx.SignalFx().rest('authkey') as sfx:
                orig_detector = json.loads(responses_map[name]['content'])
                detector = sfx.get_detector('abc123')
                self.assertEqual(orig_detector['id'], detector['id'])

    def test_get_detector_incidents(self):
        name = 'GET_DETECTOR_INCIDENTS'
        with HTTMock(mock_maker(name)):
            with signalfx.SignalFx().rest('authkey') as sfx:
                incidents = sfx.get_detector_incidents('abc123')
                self.assertEqual(0, len(incidents))

    def test_get_detector_events(self):
        name = 'GET_DETECTOR_EVENTS'
        with HTTMock(mock_maker(name)):
            with signalfx.SignalFx().rest('authkey') as sfx:
                events = sfx.get_detector_events('abc123')
                self.assertEqual(0, len(events))

    def test_get_incidents(self):
        name = 'GET_INCIDENTS'
        with HTTMock(mock_maker(name)):
            with signalfx.SignalFx().rest('authkey') as sfx:
                orig_incidents = json.loads(responses_map[name]['content'])
                incidents = sfx.get_incidents(include_resolved=True)
                self.assertEqual(len(orig_incidents), len(incidents))

    def test_get_incident(self):
        name = 'GET_INCIDENT'
        with HTTMock(mock_maker(name)):
            with signalfx.SignalFx().rest('authkey') as sfx:
                orig_incident = json.loads(responses_map[name]['content'])
                incident = sfx.get_incident('abc123')
                self.assertEqual(orig_incident['incidentId'], incident['incidentId'])

    def test_clear_incident(self):
        name = 'CLEAR_INCIDENT'
        with HTTMock(mock_maker(name)):
            with signalfx.SignalFx().rest('authkey') as sfx:
                resp = sfx.clear_incident('abc123')
                self.assertEqual(200, resp.status_code)

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
