# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import certifi
import urllib3

from . import computation


class Client(object):
    """SignalFlow client.

    Client for SignalFx's SignalFlow real-time analytics API. Allows for the
    execution of ad-hoc computations, returning its output in real-time, as it
    is produced.
    """

    _SIGNALFLOW_ENDPOINT = '/v2/signalflow'
    _SIGNALFLOW_EXECUTE_ENDPOINT = '{0}/execute'.format(_SIGNALFLOW_ENDPOINT)

    def __init__(self, api_endpoint, api_token):
        pool_args = {
            'url': api_endpoint,
            'headers': {
                'Content-Type': 'text/plain',
                'X-SF-Token': api_token
            }
        }

        if urllib3.util.parse_url(api_endpoint).scheme == 'https':
            pool_args.update({
                'cert_reqs': 'CERT_REQUIRED',  # Force certificate check.
                'ca_certs': certifi.where()    # Path to the Certifi bundle.
            })

        self._http = urllib3.connectionpool.connection_from_url(**pool_args)

    def execute(self, program, start=None, stop=None, resolution=None,
                max_delay=None, persistent=False):
        """Execute the given SignalFlow program and stream the output back."""
        params = {
            'start': start,
            'stop': stop,
            'resolution': resolution,
            'maxDelay': max_delay,
            'persistent': persistent,
        }
        params = dict((k, v) for k, v in params.items() if v)
        return computation.Computation(self._http,
                                       Client._SIGNALFLOW_EXECUTE_ENDPOINT,
                                       program, params)

    def close(self):
        self._http.close()
        self._http = None
