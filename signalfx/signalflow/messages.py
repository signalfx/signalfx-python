# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import json
import logging


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
        if payload['event'] == 'CHANNEL_ABORT':
            return ChannelAbortMessage.decode(payload)
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

    @property
    def digest(self):
        return self._digest

    @staticmethod
    def decode(payload):
        return DigestMessage(payload['timestampMs'], payload['digest'])


class ChannelAbortMessage(ControlMessage):

    def __init__(self, timestamp_ms, abort_info):
        super(ChannelAbortMessage, self).__init__(timestamp_ms)
        self._abort_info = abort_info

    @property
    def abort_info(self):
        return self._abort_info

    @staticmethod
    def decode(payload):
        return ChannelAbortMessage(payload['timestampMs'],
                                   payload['abortInfo'])


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
