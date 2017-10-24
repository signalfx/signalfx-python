# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import logging

_logger = logging.getLogger(__name__)


class StreamMessage(object):
    """Base class for stream messages received from a SignalFlow
    computation."""

    @staticmethod
    def decode(mtype, payload):
        if mtype == 'control-message':
            return ControlMessage.decode(payload)
        if mtype == 'message':
            return InfoMessage.decode(payload)
        if mtype == 'event':
            return EventMessage.decode(payload)
        if mtype == 'metadata':
            return MetadataMessage.decode(payload)
        if mtype == 'expired-tsid':
            return ExpiredTsIdMessage.decode(payload)
        if mtype == 'data':
            return DataMessage.decode(payload)
        if mtype == 'error':
            return ErrorMessage.decode(payload)
        _logger.warn('Unsupported event type; ignoring %s: %s!',
                     mtype, payload)
        return None


class ControlMessage(StreamMessage):
    """Base class for control messages."""

    def __init__(self, timestamp_ms):
        self._timestamp_ms = timestamp_ms

    @property
    def timestamp_ms(self):
        """The wall clock timestamp (millisecond precision) of the message."""
        return self._timestamp_ms

    @staticmethod
    def decode(payload):
        if payload['event'] == 'STREAM_START':
            return StreamStartMessage.decode(payload)
        if payload['event'] == 'JOB_START':
            return JobStartMessage.decode(payload)
        if payload['event'] == 'JOB_PROGRESS':
            return JobProgressMessage.decode(payload)
        if payload['event'] == 'CHANNEL_ABORT':
            return ChannelAbortMessage.decode(payload)
        if payload['event'] == 'END_OF_CHANNEL':
            return EndOfChannelMessage.decode(payload)
        _logger.warn('Unsupported control message %s; ignoring!',
                     payload['event'])
        return None


class StreamStartMessage(ControlMessage):
    """Message received when the stream begins."""

    def __init__(self, timestamp_ms):
        super(StreamStartMessage, self).__init__(timestamp_ms)

    @staticmethod
    def decode(payload):
        return StreamStartMessage(payload['timestampMs'])


class JobStartMessage(ControlMessage):
    """Message received when the SignalFlow computation has started."""

    def __init__(self, timestamp_ms, handle):
        super(JobStartMessage, self).__init__(timestamp_ms)
        self._handle = handle

    @property
    def handle(self):
        """The computation's handle ID."""
        return self._handle

    @staticmethod
    def decode(payload):
        return JobStartMessage(payload['timestampMs'], payload['handle'])


class JobProgressMessage(ControlMessage):
    """Message received while computation windows are primed, if they are
    present. The message will be received multiple times with increasing
    progress values from 0 to 100, indicating the progress percentage."""

    def __init__(self, timestamp_ms, progress):
        super(JobProgressMessage, self).__init__(timestamp_ms)
        self._progress = progress

    @property
    def progress(self):
        """Computation priming progress, as a percentage between 0 and 100."""
        return self._progress

    @staticmethod
    def decode(payload):
        return JobProgressMessage(payload['timestampMs'], payload['progress'])


class ChannelAbortMessage(ControlMessage):
    """Message received when the computation aborted before its defined stop
    time, either because of an error or from a manual stop. No further messages
    will be received from a computation after this one."""

    def __init__(self, timestamp_ms, abort_info):
        super(ChannelAbortMessage, self).__init__(timestamp_ms)
        self._abort_info = abort_info

    @property
    def abort_info(self):
        """Information about the computation's termination."""
        return self._abort_info

    @staticmethod
    def decode(payload):
        return ChannelAbortMessage(payload['timestampMs'],
                                   payload['abortInfo'])


class EndOfChannelMessage(ControlMessage):
    """Message received when the computation completes normally. No further
    messages will be received from a computation after this one."""

    def __init__(self, timestamp_ms):
        super(EndOfChannelMessage, self).__init__(timestamp_ms)

    @staticmethod
    def decode(payload):
        return EndOfChannelMessage(payload['timestampMs'])


class InfoMessage(StreamMessage):
    """Message containing information about the SignalFlow computation's
    behavior or decisions."""

    def __init__(self, logical_timestamp_ms, message):
        self._logical_timestamp_ms = logical_timestamp_ms
        self._message = message

    @property
    def logical_timestamp_ms(self):
        """The logical timestamp (millisecond precision) for which the message
        has been emitted."""
        return self._logical_timestamp_ms

    @property
    def message(self):
        """The information message. Refer to the Developer's documentation for
        a reference of the possible messages and their structure."""
        return self._message

    @staticmethod
    def decode(payload):
        return InfoMessage(payload['logicalTimestampMs'], payload['message'])


class EventMessage(StreamMessage):
    """Message received when the computation has generated an event or alert
    from a detect block."""

    def __init__(self, tsid, timestamp_ms, metadata, properties):
        self._tsid = tsid
        self._timestamp_ms = timestamp_ms
        self._metadata = metadata
        self._properties = properties

    @property
    def tsid(self):
        """The event timeseries ID."""
        return self._tsid

    @property
    def timestamp_ms(self):
        """The timestamp of the event (millisecond precision)."""
        return self._timestamp_ms

    @property
    def metadata(self):
        """The metadata of the EventTimeSeries the event belongs to. This may
        be empty for events created by the SignalFlow computation itself."""
        return self._metadata

    @property
    def properties(self):
        """The properties of the event. For alerts, you can expect 'was' and
        'is' properties that communicate the evolution of the state of the
        incident."""
        return self._properties

    @staticmethod
    def decode(payload):
        return EventMessage(payload['tsId'],
                            payload['timestampMs'],
                            payload['metadata'],
                            payload['properties'])


class MetadataMessage(StreamMessage):
    """Message containing metadata information about an output metric or event
    timeseries. Metadata messages are always emitted by the computation prior
    to any data or events for the corresponding timeseries."""

    def __init__(self, tsid, properties):
        self._tsid = tsid
        self._properties = properties

    @property
    def tsid(self):
        """A unique timeseries identifier."""
        return self._tsid

    @property
    def properties(self):
        """The metadata properties of the timeseries."""
        return self._properties

    @staticmethod
    def decode(payload):
        return MetadataMessage(payload['tsId'], payload['properties'])


class ExpiredTsIdMessage(StreamMessage):
    """Message informing us that an output timeseries is no longer part of the
    computation and that we may do some cleanup of whatever internal state we
    have tied to that output timeseries."""

    def __init__(self, tsid):
        self._tsid = tsid

    @property
    def tsid(self):
        """The identifier of the timeseries that's no longer interesting to the
        computation."""
        return self._tsid

    @staticmethod
    def decode(payload):
        return ExpiredTsIdMessage(payload['tsId'])


class DataMessage(StreamMessage):
    """Message containing a batch of datapoints generated for a particular
    iteration."""

    def __init__(self, logical_timestamp_ms, data):
        self._logical_timestamp_ms = logical_timestamp_ms
        self._data = dict((datum['tsId'], datum['value']) for datum in data)

    @property
    def logical_timestamp_ms(self):
        """The logical timestamp of the data (millisecond precision)."""
        return self._logical_timestamp_ms

    @property
    def data(self):
        """The data, as a dictionary of timeseries ID to datapoint value."""
        return self._data

    def add_data(self, data):
        self._data.update(data)

    @staticmethod
    def decode(payload):
        return DataMessage(payload['logicalTimestampMs'], payload['data'])


class ErrorMessage(StreamMessage):
    """Message received when the computation encounters errors during its
    initialization."""

    def __init__(self, errors):
        self._errors = errors

    @property
    def errors(self):
        """The list of errors. Each error has a 'code' defining what the error
        is, and a 'context' dictionary providing details."""
        return self._errors

    @staticmethod
    def decode(payload):
        return ErrorMessage(payload['errors'])
