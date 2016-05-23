# Copyright (C) 2016 SignalFx, Inc. All rights reserved.


class _SignalFlowTransport(object):
    """Base class for transports to the SignalFlow API.

    A "transport" is the communication medium used to interact with the
    SignalFlow API. There are two available transports at this time:
    Server-Sent Events over HTTP (sse) and WebSocket (ws). The former allows
    for multiplexing multiple computation channels onto the same authenticated
    WebSocket connection.
    """

    def __init__(self, api_endpoint, token):
        """Initialize the transport to the given endpoint, using the given
        authorization token."""
        self._api_endpoint = api_endpoint
        self._token = token
