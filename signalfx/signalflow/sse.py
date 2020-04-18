# Copyright (C) 2016-2019 SignalFx, Inc. All rights reserved.
# Copyright (C) 2020 Splunk, Inc. All rights reserved.

import certifi
import json
import sseclient
import urllib3

from . import channel, errors, messages, transport
from .. import constants, version


class SSETransport(transport._SignalFlowTransport):
    """Server-Sent Events transport.

    Implements a transport to the SignalFlow API that uses simple HTTP requests
    and reads Server-Sent Events streams back from SignalFx. One connection per
    SignalFlow computation is required when using this transport.

    This is a good transport for single, ad-hoc computations. For most use
    cases though, the WebSocket-based transport is more efficient and has lower
    latency.
    """

    _SIGNALFLOW_ENDPOINT = 'v2/signalflow'

    def __init__(self, token, endpoint=constants.DEFAULT_STREAM_ENDPOINT,
                 timeout=constants.DEFAULT_TIMEOUT, compress=True,
                 proxy_url=None):
        super(SSETransport, self).__init__(token, endpoint, timeout)
        pool_args = {
            'url': self._endpoint,
            'headers': {
                'Content-Type': 'text/plain',
                'X-SF-Token': self._token,
                'User-Agent': '{} urllib3/{}'.format(version.user_agent,
                                                     urllib3.__version__)
            },
            'timeout': urllib3.Timeout(connect=self._timeout, read=None),
        }

        if urllib3.util.parse_url(self._endpoint).scheme == 'https':
            pool_args.update({
                'cert_reqs': 'CERT_REQUIRED',  # Force certificate check.
                'ca_certs': certifi.where()    # Path to the Certifi bundle.
            })

        if proxy_url:
            proxy_manager = urllib3.poolmanager.proxy_from_url(proxy_url)
            endpoint = pool_args.pop('url')
            self._http = proxy_manager.connection_from_url(
                    endpoint, pool_kwargs=pool_args)
        else:
            self._http = urllib3.connectionpool.connection_from_url(
                    **pool_args)

    def __str__(self):
        return 'sse+{0}'.format(self._endpoint)

    def close(self):
        self._http.close()

    def _post(self, url, fields=None, body=None):
        r = self._http.request_encode_url('POST', url,
                                          fields=fields, body=body,
                                          preload_content=False)
        if r.status != 200:
            try:
                if r.headers['Content-Type'] == 'application/json':
                    rbody = json.loads(r.read())
                    raise errors.SignalFlowException(
                            r.status,
                            rbody.get('message'),
                            rbody.get('errorType'))
                raise errors.SignalFlowException(r.status)
            finally:
                r.close()

        return sseclient.SSEClient(r)

    def execute(self, program, params):
        url = '{endpoint}/{path}/execute'.format(
            endpoint=self._endpoint,
            path=SSETransport._SIGNALFLOW_ENDPOINT)
        return SSEComputationChannel(self._post(url, fields=params,
                                                body=program))

    def preflight(self, program, params):
        url = '{endpoint}/{path}/preflight'.format(
            endpoint=self._endpoint,
            path=SSETransport._SIGNALFLOW_ENDPOINT)
        return SSEComputationChannel(self._post(url, fields=params,
                                                body=program))

    def start(self, program, params):
        url = '{endpoint}/{path}/start'.format(
            endpoint=self._endpoint,
            path=SSETransport._SIGNALFLOW_ENDPOINT)
        self._post(url, fields=params, body=program)

    def attach(self, handle, params):
        url = '{endpoint}/{path}/{handle}/attach'.format(
            endpoint=self._endpoint,
            path=SSETransport._SIGNALFLOW_ENDPOINT,
            handle=handle)
        return SSEComputationChannel(self._post(url, fields=params))

    def keepalive(self, handle):
        url = '{endpoint}/{path}/{handle}/keepalive'.format(
            endpoint=self._endpoint,
            path=SSETransport._SIGNALFLOW_ENDPOINT,
            handle=handle)
        self._port(url)

    def stop(self, handle, params):
        url = '{endpoint}/{path}/{handle}/stop'.format(
            endpoint=self._endpoint,
            path=SSETransport._SIGNALFLOW_ENDPOINT,
            handle=handle)
        self._port(url, fields=params)


class SSEComputationChannel(channel._Channel):
    """Computation channel fed from a Server-Sent Events stream."""

    def __init__(self, stream):
        super(SSEComputationChannel, self).__init__()
        self._stream = stream
        self._events = stream.events()

    def _next(self):
        event = next(self._events)
        payload = json.loads(event.data)
        return messages.StreamMessage.decode(event.event, payload)

    def close(self):
        self._stream.close()
