"""SignalFx python client AWS integration module

Provides a set of functions and attributes to integrate the SignalFx python
client library with Amazon Web Services (AWS).

Example usage to include an AWS unique ID dimension with every
datapoint and event:

    import signalfx
    from signalfx.aws import AWS_ID_DIMENSION, get_aws_unique_id

    sfx = signalfx.SignalFx('your_api_token')
    sfx.add_dimensions({AWS_ID_DIMENSION: get_aws_unique_id()})
    sfx.send(
        gauges=[
          {
            'metric': 'myfunc.time',
            'value': 532,
            'timestamp': 1442960607000
            'dimensions': {'host': 'server1', 'host_ip': '1.2.3.4'}
          },
        ])
"""

# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

import logging
import requests

AWS_ID_DIMENSION = 'AWSUniqueId'
AWS_ID_URL = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
DEFAULT_AWS_TIMEOUT = 1  # Timeout to connect to the AWS metadata service

_logger = logging.getLogger(__name__)


def get_aws_unique_id(timeout=DEFAULT_AWS_TIMEOUT):
    """Determine the current AWS unique ID

    Args:
        timeout (int): How long to wait for a response from AWS metadata IP
    """
    try:
        resp = requests.get(AWS_ID_URL, timeout=timeout).json()
    except requests.exceptions.ConnectTimeout:
        _logger.warning('Connection timeout when determining AWS unique '
                        'ID. Not using AWS unique ID.')
        return None
    else:
        aws_id = "{0}_{1}_{2}".format(resp['instanceId'], resp['region'],
                                      resp['accountId'])
        _logger.debug('Using AWS unique ID %s.', aws_id)
        return aws_id
