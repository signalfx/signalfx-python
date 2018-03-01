# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

# Default Parameters
DEFAULT_INGEST_ENDPOINT = 'https://ingest.signalfx.com'
DEFAULT_API_ENDPOINT = 'https://api.signalfx.com'
DEFAULT_STREAM_ENDPOINT = 'https://stream.signalfx.com'
DEFAULT_BATCH_SIZE = 300  # Will wait for this many requests before posting
DEFAULT_TIMEOUT = 5

# Integer Boundaries
INTEGER_MAX = (2**63)-1
INTEGER_MIN = -(2**63)

# Global Parameters
SUPPORTED_EVENT_CATEGORIES = [
    'ALERT',
    'AUDIT',
    'COLLECTD',
    'EXCEPTION',
    'JOB',
    'SERVICE_DISCOVERY',
    'USER_DEFINED',
]
