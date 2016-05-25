# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import base64
import json
import logging
from six.moves import queue
import struct
from ws4py.client.threadedclient import WebSocketClient

from . import channel, messages, transport


class WebSocketTransport(transport._SignalFlowTransport, WebSocketClient):
    """WebSocket based transport.

    Uses the SignalFlow WebSocket connection endpoint to interact with
    SignalFx's SignalFlow API. Multiple computation streams can be multiplexed
    through a single, pre-opened WebSocket connection. It also utilizes a more
    efficient binary encoding for data so it requires less bandwidth and has
    overall less latency.
    """

    _SIGNALFLOW_WEBSOCKET_ENDPOINT = 'v2/signalflow/connect'

    def __init__(self, api_endpoint, token):
        transport._SignalFlowTransport.__init__(
                self,
                api_endpoint.replace('http', 'ws', 1),
                token)

        self._ws_endpoint = '{0}/{1}'.format(
                self._api_endpoint,
                WebSocketTransport._SIGNALFLOW_WEBSOCKET_ENDPOINT)
        WebSocketClient.__init__(self, self._ws_endpoint,
                                 heartbeat_freq=None)

        self._server_time = None
        self._connected = False
        self._channels = {}

    def __str__(self):
        return self._ws_endpoint

    def close(self, code=1001, reason=None):
        if not self._connected:
            return
        WebSocketClient.close(self, code, reason)

    def execute(self, program, params):
        channel = WebSocketComputationChannel(self.detach)

        request = {
            'type': 'execute',
            'channel': channel.name,
            'program': program
        }
        request.update(params)

        self._channels[channel.name] = channel
        self._send(request)
        return channel

    def start(self, program, params):
        request = {'type': 'start'}
        request.update(params)
        self._send(json.dumps(request))

    def attach(self, handle, params):
        channel = WebSocketComputationChannel(self.detach)

        request = {
            'type': 'attach',
            'channel': channel.name,
            'handle': handle
        }
        request.update(params)

        self._channels[channel.name] = channel
        self._send(request)
        return channel

    def detach(self, channel):
        if channel.name not in self._channels:
            return

        request = {
            'type': 'detach',
            'channel': channel.name
        }

        del self._channels[channel.name]
        self._send(request)

    def keepalive(self, handle):
        request = {'type': 'keepalive', 'handle': handle}
        self._send(request)

    def stop(self, handle, params):
        request = {'type': 'stop'}
        request.update(params)
        self._send(request)

    def _send(self, request):
        if not self._connected:
            self.connect()
        self.send(json.dumps(request))

    def opened(self):
        # Send authentication request
        request = {'type': 'authenticate', 'token': self._token}
        self.send(json.dumps(request))
        self._connected = True

    def received_message(self, message):
        decoded = None
        if message.is_binary:
            # Binary messages use a custom encoding format. First, unpack the
            # header with the encoding version, message type and channel name.
            # The rest of the encoding depends on the message type.
            version, mtype, channel = struct.unpack(
                    '!BBxx16s',
                    message.data[:20])

            decoded = {
                'channel': channel
            }

            if mtype == 5:
                # Decode data batch message
                timestamp, data = self._decode_databatch(message.data[20:])
                decoded.update({
                    'type': 'data',
                    'logicalTimestampMs': timestamp,
                    'data': data
                })
            else:
                logging.warn('Unsupported binary message type %s!', mtype)
        else:
            decoded = json.loads(message.data)

        if decoded:
            self._process_message(decoded)

    def _process_message(self, message):
        if message.get('event') == 'KEEP_ALIVE':
            self._server_time = message.get('timestampMs', self._server_time)
            return

        channel = message.get('channel')
        if not channel or channel not in self._channels:
            logging.warn('Received message for unknown channel (%s)', channel)
            return

        self._channels[channel].offer(message)

        if message.get('type') in ['END_OF_CHANNEL', 'ABORT_CHANNEL']:
            self._channels[channel].offer(
                    WebSocketComputationChannel.END_SENTINEL)
            del self._channels[channel]

    def _decode_databatch(self, data):
        def chunks(l, n):
            """Yield successive n-sized chunks from l."""
            for i in xrange(0, len(l), n):
                yield l[i:i+n]

        timestamp, count = struct.unpack('!qi', data[:12])
        datapoints = []
        for chunk in chunks(data[12:], 17):
            vtype, = struct.unpack('!B', chunk[0])
            tsId = base64.urlsafe_b64encode(chunk[1:9]).replace('=', '')
            value, = struct.unpack('!q' if vtype == 1 else '!d', chunk[9:])
            datapoints.append({'tsId': tsId, 'value': value})
        return timestamp, datapoints

    def closed(self, code, reason=None):
        logging.warn('Lost WebSocket connection with %s channels: %s %s.',
                     len(self._channels), code, reason)
        self._channels.clear()
        self._connected = False


class WebSocketComputationChannel(channel._Channel):
    """Computation channel fed from a WebSocket channel."""

    END_SENTINEL = object()

    def __init__(self, detach_func):
        super(WebSocketComputationChannel, self).__init__()
        self._detach_func = detach_func
        self._q = queue.Queue()

    def offer(self, message):
        self._q.put(message)

    def _next(self):
        while True:
            try:
                event = self._q.get(timeout=0.1)
                if event == WebSocketComputationChannel.END_SENTINEL:
                    raise StopIteration()
                return messages.StreamMessage.decode(event['type'], event)
            except queue.Empty:
                pass

    def close(self):
        self._detach_func(self)
