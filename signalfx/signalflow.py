# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import certifi
import json
import logging
import sseclient
import urllib3


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

    def execute(self, program, start, stop=None, resolution=None,
                max_delay=None, persistent=False):
        """Execute the given SignalFlow program and stream the output back."""
        if not program or not start:
            raise ValueError()

        # Build query parameters
        params = {
            'start': start,
            'stop': stop,
            'resolution': resolution,
            'maxDelay': max_delay,
            'persistent': persistent,
        }
        params = dict((k, v) for k, v in params.items() if v)
        return Computation(self._http, Client._SIGNALFLOW_EXECUTE_ENDPOINT,
                           program, params)

    def close(self):
        self._http.close()
        self._http = None


class ComputationExecutionError(Exception):

    def __init__(self, code, message=None):
        self._code = code
        self._message = message

    @property
    def code(self):
        return self._code

    @property
    def message(self):
        return self._message

    def __str__(self):
        return self._message


class Computation(object):
    """A live handle to a running SignalFlow computation.

    A computation object allows access to the computation's output in real-time
    via the stream() method. It automatically analyzes the incoming stream
    messages and presents the computation's data and metadata output in a
    conveniently consumable way.
    """

    _CONTROL_MESSAGE_TYPE = 'CONTROL'
    _METADATA_MESSAGE_TYPE = 'METADATA'
    _DATA_MESSAGE_TYPE = 'DATA'
    _EVENT_MESSAGE_TYPE = 'EVENT'

    _REPR_IGNORED_DIMENSIONS = set(['sf_metric',
                                    'sf_eventType',
                                    'jobId',
                                    'programId'])

    def __init__(self, conn, url, program, params):
        self._id = None
        self._conn = conn
        self._url = url
        self._program = program
        self._params = params

        self._progress = 0
        self._complete = False
        self._resolution = None
        self._metadata = {}
        self._last_logical_ts = None

        r = self._conn.request_encode_url(
                'POST', self._url,
                fields=self._params, body=self._program,
                preload_content=False)
        if r.status != 200:
            try:
                if r.headers['Content-Type'] == 'application/json':
                    raise ComputationExecutionError(**json.loads(r.read()))
                raise ComputationExecutionError(r.status)
            finally:
                r.close()

        self._events = sseclient.SSEClient(r)

    @property
    def id(self):
        return self._id

    @property
    def program(self):
        return self._program

    @property
    def progress(self):
        return self._progress

    @property
    def resolution(self):
        return self._resolution

    def is_complete(self):
        return self._complete

    def get_known_tsids(self):
        return sorted(self._metadata.keys())

    def get_metadata(self, tsid):
        """Return the full metadata object for the given timeseries (by its
        ID), if available."""
        return self._metadata.get(tsid)

    def get_timeseries_repr(self, tsid):
        """Return a representation of a timeseries' identity usable for
        display. If the timeseries type has a known fixed dimension, it is
        promoted to the front of the representation."""
        obj = self.get_metadata(tsid)
        if not obj:
            return None

        result = []

        if obj['sf_type'] == 'MetricTimeSeries':
            result.append(obj['sf_metric'])
        elif obj['sf_type'] == 'EventTimeSeries':
            result.append(obj['sf_eventType'])

        key = filter(lambda k: k not in Computation._REPR_IGNORED_DIMENSIONS,
                     obj['sf_key'])
        name = '.'.join(map(lambda k: obj[k], sorted(key)))
        result.append(name)

        return '/'.join(filter(None, result))

    def stream(self):
        """Iterate over the messages from the computation's output.

        Control and metadata messages are intercepted and interpreted to
        enhance this Computation's object knowledge of the computation's
        context. Data and event messages are yielded back to the caller as a
        generator.
        """

        # TODO(mpetazzoni): automatically re-issue the query with Last-Event-ID
        # header on httplib.IncompleteRead exceptions.

        last_data_batch = None
        for event in self._events.events():
            message = StreamMessage.decode(event)
            if isinstance(message, EndOfChannelMessage):
                self._complete = True
                break

            if isinstance(message, JobProgressMessage):
                self._progress = message.progress
                continue

            # Intercept metadata messages to accumulate received metadata.
            # TODO(mpetazzoni): this can accumulate metadata without bounds if
            # a computation has a high rate of member churn.
            if isinstance(message, MetadataMessage):
                self._metadata[message.tsid] = message.properties
                continue

            if isinstance(message, DigestMessage):
                self._process_message_digest(message.digest)
                continue

            # Automatically and immediately yield events.
            if isinstance(message, EventMessage):
                yield message

            # Accumulate data messages and release them when we have received
            # all batches for the same logical timestamp.
            if isinstance(message, DataMessage):
                if not last_data_batch:
                    last_data_batch = message
                elif message.logical_timestamp_ms == \
                        last_data_batch.logical_timestamp_ms:
                    last_data_batch.add_data(message.data)
                else:
                    to_yield, last_data_batch = last_data_batch, message
                    self._last_logical_ts = to_yield.logical_timestamp_ms
                    yield to_yield

        # Yield last batch, even if potentially incomplete.
        if last_data_batch:
            yield last_data_batch

    def close(self):
        """Manually close this computation's output if its stream wasn't
        entirely consumed."""
        self._events.close()

    def _process_message_digest(self, digest):
        for message in digest:
            if message['messageCode'] == 'JOB_RUNNING_RESOLUTION':
                self._resolution = message['jsonPayload']['resolutionMs']


class StreamMessage(object):

    @staticmethod
    def decode(event):
        payload = json.loads(event.data)
        if event.event == 'control-message':
            return ControlMessage.decode(payload)
        if event.event == 'metadata':
            return MetadataMessage.decode(payload)
        if event.event == 'event':
            return EventMessage.decode(payload)
        if event.event == 'data':
            return DataMessage.decode(payload)
        logging.warn('Unsupported event type; ignoring %s!', event)
        return None


class ControlMessage(StreamMessage):

    def __init__(self, timestamp_ms):
        self._timestamp_ms = timestamp_ms

    @property
    def timestamp_ms(self):
        return self._timestamp_ms

    @staticmethod
    def decode(payload):
        if payload['event'] == 'STREAM_START':
            return StreamStartMessage.decode(payload)
        if payload['event'] == 'JOB_START':
            return JobStartMessage.decode(payload)
        if payload['event'] == 'JOB_PROGRESS':
            return JobProgressMessage.decode(payload)
        if payload['event'] == 'MESSAGE_DIGEST':
            return DigestMessage.decode(payload)
        if payload['event'] == 'END_OF_CHANNEL':
            return EndOfChannelMessage.decode(payload)
        logging.warn('Unsupported control message %s; ignoring!',
                     payload['event'])
        return None


class StreamStartMessage(ControlMessage):

    def __init__(self, timestamp_ms):
        super(StreamStartMessage, self).__init__(timestamp_ms)

    @staticmethod
    def decode(payload):
        return StreamStartMessage(payload['timestampMs'])


class JobStartMessage(ControlMessage):

    def __init__(self, timestamp_ms):
        super(JobStartMessage, self).__init__(timestamp_ms)

    @staticmethod
    def decode(payload):
        return JobStartMessage(payload['timestampMs'])


class JobProgressMessage(ControlMessage):

    def __init__(self, timestamp_ms, progress):
        super(JobProgressMessage, self).__init__(timestamp_ms)
        self._progress = progress

    @property
    def progress(self):
        return self._progress

    @staticmethod
    def decode(payload):
        return JobProgressMessage(payload['timestampMs'], payload['progress'])


class DigestMessage(ControlMessage):

    def __init__(self, timestamp_ms, digest):
        super(DigestMessage, self).__init__(timestamp_ms)
        self._digest = digest
        for message in self._digest:
            payload = message.get('jsonPayload')
            if payload:
                message['jsonPayload'] = json.loads(payload)

    @property
    def digest(self):
        return self._digest

    @staticmethod
    def decode(payload):
        return DigestMessage(payload['timestampMs'], payload['digest'])


class EndOfChannelMessage(ControlMessage):

    def __init__(self, timestamp_ms):
        super(EndOfChannelMessage, self).__init__(timestamp_ms)

    @staticmethod
    def decode(payload):
        return EndOfChannelMessage(payload['timestampMs'])


class MetadataMessage(StreamMessage):

    def __init__(self, tsid, properties):
        self._tsid = tsid
        self._properties = properties

    @property
    def tsid(self):
        return self._tsid

    @property
    def properties(self):
        return self._properties

    @staticmethod
    def decode(payload):
        return MetadataMessage(payload['tsId'], payload['properties'])


class DataMessage(StreamMessage):

    def __init__(self, logical_timestamp_ms, data):
        self._logical_timestamp_ms = logical_timestamp_ms
        self._data = dict((datum['tsId'], datum['value']) for datum in data)

    @property
    def logical_timestamp_ms(self):
        return self._logical_timestamp_ms

    @property
    def data(self):
        return self._data

    def add_data(self, data):
        self._data.update(data)

    @staticmethod
    def decode(payload):
        return DataMessage(payload['logicalTimestampMs'], payload['data'])


class EventMessage(StreamMessage):

    def __init__(self, timestamp_ms, properties):
        self._timestamp_ms = timestamp_ms
        self._properties = properties

    @property
    def timestamp_ms(self):
        return self._timestamp_ms

    @property
    def properties(self):
        return self._properties

    @staticmethod
    def decode(payload):
        return EventMessage(payload['timestampMs'], payload['properties'])
