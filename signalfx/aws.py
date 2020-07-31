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
DEFAULT_AWS_TIMEOUT = 1  # Timeout to connect to the AWS metadata service

# https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-metadata.html
EC2_ID_URL = 'http://169.254.169.254/latest/dynamic/instance-identity/document'
# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint.html
ECS_METADATA_URL = 'http://169.254.170.2/v2/metadata'

_logger = logging.getLogger(__name__)


def get_aws_unique_id(timeout=DEFAULT_AWS_TIMEOUT):
    """Determine the current AWS unique ID by trying the ECS metadata service
    and then the EC2 metadata service.

    Args:
        timeout (int): How long to wait for response from AWS metadata service
    """
    try:
        resp = requests.get(ECS_METADATA_URL, timeout=timeout)
        # ECS metadata service returns a 400 (HTTPError)
        # if we're not an ECS task
        resp.raise_for_status()
        task_arn = resp.json()['TaskARN']
        # arn:aws:ecs:region:account-id:task/task-id
        [_, _, _, region, account_id, task] = task_arn.split(':', 6)
        task_id = task.split('/', 1)[1]
        aws_id = '{0}_{1}_{2}'.format(task_id, region, account_id)
    except (requests.exceptions.HTTPError, requests.exceptions.ConnectTimeout):
        try:
            data = requests.get(EC2_ID_URL, timeout=timeout).json()
        except requests.exceptions.ConnectTimeout:
            _logger.warning('Connection timeout when determining AWS unique '
                            'ID. Not using AWS unique ID.')
            return None
        aws_id = '{0}_{1}_{2}'.format(data['instanceId'], data['region'],
                                      data['accountId'])
    _logger.debug('Using AWS unique ID %s.', aws_id)
    return aws_id
