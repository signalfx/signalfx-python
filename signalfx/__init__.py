"""
SignalFx client library.

This module makes interacting with SignalFx from your Python scripts and
applications easy by providing a full-featured client for SignalFx's APIs.

Basic usage:

    import signalfx

    sfx = signalfx.SignalFx('your_api_token')
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

Read the documentation at https://github.com/signalfx/signalfx-python for more
in depth examples.
"""

# Copyright (C) 2015 SignalFx, Inc. All rights reserved.

import logging

import client
from constants import *  # flake8: noqa


__author__ = 'SignalFx, Inc'
__email__ = 'support+python@signalfx.com'
__copyright__ = 'Copyright (C) 2015 SignalFx, Inc. All rights reserved.'
__all__ = ['SignalFx']

SignalFxLoggingStub = client.BaseSignalFx
if client.sf_pbuf:
    SignalFx = client.ProtoBufSignalFx
else:
    logging.warn('Protocol Buffers not installed properly. Switching to Json.')
    SignalFx = client.JsonSignalFx
