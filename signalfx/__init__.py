"""
SignalFx client library.

This module makes interacting with SignalFx from your Python scripts and
applications easy by providing a full-featured client for SignalFx's APIs.

Basic usage for reporting data:

    import signalfx

    sfx = signalfx.SignalFx().ingest('your_api_token')
    sfx.send(
        gauges=[
          {
            'metric': 'myfunc.time',
            'value': 532,
            'timestamp': 1442960607000,
            'dimensions': {'host': 'server1', 'host_ip': '1.2.3.4'}
          },
        ])

    import atexit
    atexit.register(sfx.stop)

Example of executing a SignalFlow computation:

    import signalfx

    program = "data('cpu.utilization').mean().publish()"
    flow = signalfx.SignalFx().signalflow('your_user_token')
    for msg in flow.execute(program).stream():
        if isinstance(msg, signalfx.signalflow.messages.DataMessage):
            print(msg.data)
    flow.stop()

Read the documentation at https://github.com/signalfx/signalfx-python for more
in-depth examples.
"""

# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

import logging
import requests

from constants import DEFAULT_API_ENDPOINT, DEFAULT_INGEST_ENDPOINT, \
        DEFAULT_STREAM_ENDPOINT, DEFAULT_TIMEOUT
import ingest
import rest
import signalflow


__author__ = 'SignalFx, Inc'
__email__ = 'support+python@signalfx.com'
__copyright__ = 'Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.'
__all__ = ['SignalFx']


class SignalFx(object):
    """SignalFx client.

    This base gives access to the various API clients to interact with the
    SignalFx ingest API, the SignalFx metadata REST API and SignalFx's
    SignalFlow API.
    """

    def __init__(self, api_endpoint=DEFAULT_API_ENDPOINT,
                 ingest_endpoint=DEFAULT_INGEST_ENDPOINT,
                 stream_endpoint=DEFAULT_STREAM_ENDPOINT,
                 timeout=DEFAULT_TIMEOUT):
        self._api_endpoint = api_endpoint
        self._ingest_endpoint = ingest_endpoint
        self._stream_endpoint = stream_endpoint
        self._timeout = timeout

    def login(self, email, password):
        """Authenticate a user with SignalFx to acquire a session token.

        Note that data ingest can only be done with an organization or team API
        access token, not with a user token obtained via this method.

        Args:
            email (string): the email login
            password (string): the password
        Returns a new, immediately-usable session token for the logged in user.
        """
        r = requests.post('{0}/v2/session'.format(self._api_endpoint),
                          json={'email': email, 'password': password})
        r.raise_for_status()
        return r.json()['accessToken']

    def rest(self, token, endpoint=None, timeout=None):
        """Obtain a metadata REST API client."""
        return rest.SignalFxRestClient(
            token=token,
            endpoint=endpoint or self._api_endpoint,
            timeout=timeout or self._timeout)

    def ingest(self, token, endpoint=None, timeout=None):
        """Obtain a datapoint and event ingest client."""
        if ingest.sf_pbug:
            client = ingest.ProtoBufSignalFxIngestClient
        else:
            logging.warn('Protocol Buffers not installed properly; '
                         'falling back to JSON.')
            client = ingest.JsonSignalFxIngestClient
        return client(
            token=token,
            endpoint=endpoint or self._ingest_endpoint,
            timeout=timeout or self._timeout)

    def signalflow(self, token, endpoint=None, timeout=None):
        """Obtain a SignalFlow API client."""
        return signalflow.SignalFlowClient(
            token=token,
            endpoint=endpoint or self._stream_endpoint,
            timeout=timeout or self._timeout)
