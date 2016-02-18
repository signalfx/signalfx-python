# Copyright (C) 2015 SignalFx, Inc. All rights reserved.

# Default Parameters
DEFAULT_INGEST_ENDPOINT = 'https://ingest.signalfx.com'
DEFAULT_BATCH_SIZE = 300  # Will wait for this many requests before posting
DEFAULT_TIMEOUT = 1

# Global Parameters
PROTOBUF_HEADER_CONTENT_TYPE = {'Content-Type': 'application/x-protobuf'}
JSON_HEADER_CONTENT_TYPE = {'Content-Type': 'application/json'}
SUPPORTED_EVENT_CATEGORIES = ["USER_DEFINED", "ALERT",
                              "AUDIT", "JOB", "COLLECTD", "SERVICE_DISCOVERY",
                              "EXCEPTION"]
