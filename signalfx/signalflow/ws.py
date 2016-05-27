# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import base64
import json
import logging
from six.moves import queue
import struct
import threading
from ws4py.client.threadedclient import WebSocketClient

from . import channel, errors, messages, transport
from .. import constants


class WebSocketTransport(transport._SignalFlowTransport, WebSocketClient):
    """WebSocket based transport.

    Uses the SignalFlow WebSocket connection endpoint to interact with
    SignalFx's SignalFlow API. Multiple computation streams can be multiplexed
    through a single, pre-opened WebSocket connection. It also utilizes a more
    efficient binary encoding for data so it requires less bandwidth and has
    overall less latency.
    """

    _SIGNALFLOW_WEBSOCKET_ENDPOINT = 'v2/signalflow/connect'

    def __init__(self, token, endpoint=constants.DEFAULT_STREAM_ENDPOINT,
                 timeout=constants.DEFAULT_TIMEOUT):
        ws_endpoint = '{0}/{1}'.format(
                endpoint.replace('http', 'ws', 1),
                WebSocketTransport._SIGNALFLOW_WEBSOCKET_ENDPOINT)

        transport._SignalFlowTransport.__init__(self, token, ws_endpoint,
                                                timeout)
        WebSocketClient.__init__(self, self._endpoint, heartbeat_freq=None)

        self._server_time = None
        self._connected = False
        self._error = None

        self._connection_cv = threading.Condition()
        self._channels = {}

    def __str__(self):
        return self._endpoint

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
        with self._connection_cv:
            if not self._connected:
                self.connect()
            while not self._connected and not self._error:
                self._connection_cv.wait()
            if not self._connected:
                raise self._error
        self.send(json.dumps(request))

    def opened(self):
        """Handler called when the WebSocket connection is opened. The first
        thing to do then is to authenticate ourselves."""
        request = {'type': 'authenticate', 'token': self._token}
        self.send(json.dumps(request))

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
        # Intercept KEEP_ALIVE control messages
        if message.get('type') == 'control-message' and \
                message.get('event') == 'KEEP_ALIVE':
            self._server_time = message.get('timestampMs', self._server_time)
            return

        # Authenticated messages inform us that our authentication has been
        # accepted and we can now consider the socket as "connected".
        if message.get('type') == 'authenticated':
            with self._connection_cv:
                self._connected = True
                self._connection_cv.notify()
            logging.debug('WebSocket connection authenticated as %s (in %s)',
                          message.get('userId'), message.get('orgId'))
            return

        # All other messages should have a channel.
        channel = message.get('channel')
        if not channel or channel not in self._channels:
            logging.warn('Received message for unknown channel (%s)', channel)
            return

        self._channels[channel].offer(message)

        # If we see an END_OF_CHANNEL or ABORT_CHANNEL message, we can clear
        # out our reference to said channel; nothing more will happen on it.
        if message.get('type') == 'control-message' and \
                message.get('event') in ['END_OF_CHANNEL', 'ABORT_CHANNEL']:
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
        """Handler called when the WebSocket is closed. Status code 1000
        denotes a normal close; all others are errors."""
        self._channels.clear()
        if code != 1000:
            self._error = errors.SignalFlowException(code, reason)
        with self._connection_cv:
            self._connected = False
            self._connection_cv.notify()


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

                error = event.get('error')
                if error:
                    raise errors.SignalFlowException(
                            error, event.get('message'))

                return messages.StreamMessage.decode(event['type'], event)
            except queue.Empty:
                pass

    def close(self):
        self._detach_func(self)
