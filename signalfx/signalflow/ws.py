# Copyright (C) 2016-2019 SignalFx, Inc. All rights reserved.
# Copyright (C) 2020 Splunk, Inc. All rights reserved.

import base64
import json
import logging
from six.moves import queue
import struct
import threading
import ws4py
from ws4py.client.threadedclient import WebSocketClient
import zlib

from . import channel, errors, messages, transport
from .. import constants, version

_logger = logging.getLogger(__name__)


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
                 timeout=constants.DEFAULT_TIMEOUT, compress=True,
                 proxy_url=None):
        if proxy_url:
            raise NotImplementedError('Websocket transport cannot be proxied!')

        ws_endpoint = '{0}/{1}'.format(
            endpoint.replace('http', 'ws', 1),
            WebSocketTransport._SIGNALFLOW_WEBSOCKET_ENDPOINT)

        transport._SignalFlowTransport.__init__(self, token, ws_endpoint,
                                                timeout)

        self._compress = compress
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
            'compress': self._compress,
            'program': program
        }
        request.update(params)

        self._channels[channel.name] = channel
        self._send(request)
        return channel

    def preflight(self, program, params):
        channel = WebSocketComputationChannel(self.detach)

        request = {
            'type': 'preflight',
            'channel': channel.name,
            'compress': self._compress,
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
            'compress': self._compress,
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

        self._send(request)
        channel.offer(WebSocketComputationChannel.END_SENTINEL)
        del self._channels[channel.name]

    def keepalive(self, handle):
        request = {'type': 'keepalive', 'handle': handle}
        self._send(request)

    def stop(self, handle, params):
        request = {'type': 'stop', 'handle': handle}
        request.update(params)
        self._send(request)

    def _send(self, request):
        with self._connection_cv:
            if not self._connected:
                # Clear any previous error state before attempting to
                # reconnect.
                self._error = None
                WebSocketClient.__init__(self, self._endpoint,
                                         heartbeat_freq=None)
                self.connect()
            while not self._connected and not self._error:
                self._connection_cv.wait()
            if not self._connected:
                raise self._error
        self.send(json.dumps(request))

    def opened(self):
        """Handler called when the WebSocket connection is opened. The first
        thing to do then is to authenticate ourselves."""
        request = {
            'type': 'authenticate',
            'token': self._token,
            'userAgent': '{} ws4py/{}'.format(version.user_agent,
                                              ws4py.__version__),
        }
        self.send(json.dumps(request))

    def received_message(self, message):
        decoded = None
        if message.is_binary:
            decoded = self.decode_binary_message(bytes(message.data))
        else:
            decoded = json.loads(message.data.decode('utf-8'))

        if decoded:
            self._process_message(decoded)

    def decode_binary_message(self, data):
        # Binary messages use a custom encoding format. First, unpack the
        # leading version byte to determine how to unpack the rest.
        version, = struct.unpack('!B', data[0:1])
        if version > 3:
            _logger.warn('Unsupported binary message version %s!',
                         version)
            return None

        header, data = data[:20], data[20:]
        version, mtype, flags, channel = struct.unpack('!BBBx16s', header)

        channel = ''.join(filter(lambda c: ord(c), channel.decode('utf-8')))
        is_compressed = flags & (1 << 0)
        is_json = flags & (1 << 1)

        if is_compressed:
            try:
                # 'zlib.MAX_WBITS | 16' flags value is required to correctly
                # uncompress data compressed by Java's GZIP compression.
                data = zlib.decompress(data, zlib.MAX_WBITS | 16)
            except zlib.error:
                _logger.warn('Error decompressing message contents!')
                return None

        if is_json:
            return json.loads(data.decode('utf-8'))

        if mtype == 5:
            # Decode data batch message
            if version == 1:
                timestamp, = struct.unpack('!q', data[0:8])
                max_delay = None
                data = data[8:]
            elif version == 2 or version == 3:
                timestamp, max_delay = struct.unpack('!qq', data[0:16])
                data = data[16:]

            # Parse out datapoints
            datapoints = self._decode_datapoints(data)
            return {
                'channel': channel,
                'type': 'data',
                'logicalTimestampMs': timestamp,
                'maxDelayMs': max_delay,
                'data': datapoints
            }
        else:
            _logger.warn('Unsupported binary message type %s!', mtype)
            return None

    def _process_message(self, message):
        # Intercept KEEP_ALIVE messages
        if message.get('event') == 'KEEP_ALIVE':
            self._server_time = message.get('timestampMs', self._server_time)
            return

        # Authenticated messages inform us that our authentication has been
        # accepted and we can now consider the socket as "connected".
        if message.get('type') == 'authenticated':
            with self._connection_cv:
                self._connected = True
                self._connection_cv.notify()
            _logger.debug('WebSocket connection authenticated as %s (in %s)',
                          message.get('userId'), message.get('orgId'))
            return

        # All other messages should have a channel.
        channel = message.get('channel')
        if not channel or channel not in self._channels:
            return

        self._channels[channel].offer(message)

        # If we see an END_OF_CHANNEL or ABORT_CHANNEL message, we can clear
        # out our reference to said channel; nothing more will happen on it.
        if message.get('type') == 'control-message' and \
                message.get('event') in ['END_OF_CHANNEL', 'ABORT_CHANNEL']:
            self._channels[channel].offer(
                WebSocketComputationChannel.END_SENTINEL)
            del self._channels[channel]

    def _decode_datapoints(self, data):
        def chunks(parts, n):
            """Yield successive n-sized chunks from parts."""
            for i in range(0, len(parts), n):
                yield parts[i:i+n]

        # Ignore count at data[0:4], we just go by chunks of 17.
        datapoints = []
        for chunk in chunks(data[4:], 17):
            vtype, = struct.unpack('!B', chunk[0:1])
            tsId = (base64.urlsafe_b64encode(chunk[1:9])
                    .decode('utf-8')
                    .replace('=', ''))
            value = None
            if vtype != 0:
                value, = struct.unpack('!d' if vtype == 2 else '!q', chunk[9:])
            datapoints.append({'tsId': tsId, 'value': value})
        return datapoints

    def unhandled_error(self, error):
        """Handler called on unhandled errors (socket errors, OS errors, etc).
        We don't need to do anything here as the socket will be closed, causing
        the closed() handler to be called, in which we handle the path to
        reconnection."""
        # TODO(mpetazzoni): ws4py >= 0.3.5 only?
        _logger.debug('WebSocket error: %s; will reconnect.', error)

    def closed(self, code, reason=None):
        """Handler called when the WebSocket is closed. Status code 1000
        denotes a normal close; all others are errors."""
        if code != 1000:
            self._error = errors.SignalFlowException(code, reason)
            _logger.info('Lost WebSocket connection with %s (%s: %s).',
                         self, code, reason)
            for c in self._channels.values():
                c.offer(WebSocketComputationChannel.END_SENTINEL)
        self._channels.clear()
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
