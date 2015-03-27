# Copyright (C) 2015 SignalFx, Inc. All rights reserved.

import json
import logging
import os
import requests

DEFAULT_API_ENDPOINT_URL = 'https://api.signalfx.com/v2'
DEFAULT_INGEST_ENDPOINT_URL = 'https://ingest.signalfx.com/v2'


class SignalFx(object):
    """SignalFx API client.

    This class presents a programmatic interface to SignalFx's metadata and
    ingest APIs. At the time being, only ingest is supported; more will come
    later.
    """

    def __init__(self, api_token, api_endpoint=DEFAULT_API_ENDPOINT_URL,
                 ingest_endpoint=DEFAULT_INGEST_ENDPOINT_URL, timeout=1):
        self._api_token = api_token
        self._api_endpoint = api_endpoint
        self._ingest_endpoint = ingest_endpoint
        self._timeout = timeout

    def send(self, gauges=None, counters=None):
        """Send the given metrics to SignalFx.

        Args:
            gauges (list): a list of dictionaries representing the gauges to
                report.
            counters (list): a list of dictionaries representing the counters
                to report.
        """

        if not gauges and not counters:
            return None

        # TODO: switch to protocol buffers.
        data = {'gauge': gauges, 'counter': counters}
        logging.debug('Sending to SignalFx: %s', data)
        return requests.post(
                os.path.join(self._ingest_endpoint, 'datapoint'),
                headers={'Content-Type': 'application/json',
                         'X-SF-Token': self._api_token},
                data=json.dumps(data),
                verify=True,
                timeout=self._timeout)
