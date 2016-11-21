# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

import collections
import json
import logging
import pprint
import requests
from six.moves import queue
import threading

from .constants import DEFAULT_INGEST_ENDPOINT, DEFAULT_TIMEOUT, \
        DEFAULT_BATCH_SIZE, SUPPORTED_EVENT_CATEGORIES
from . import version

try:
    from .generated_protocol_buffers \
            import signal_fx_protocol_buffers_pb2 as sf_pbuf
except ImportError:
    sf_pbuf = None


class _BaseSignalFxIngestClient(object):
    """Base SignalFx ingest client.

    This class is private and is not meant to be used directly. Instead, its
    subclasses, which implement specific data encodings for interacting with
    the SignalFx Ingest API.

    This class manages the datapoint sending thread and the common features.
    """

    _THREAD_NAME = 'SignalFxDatapointSendThread'

    _HEADER_API_TOKEN_KEY = 'X-SF-Token'
    _HEADER_USER_AGENT_KEY = 'User-Agent'

    _INGEST_ENDPOINT_DATAPOINT_SUFFIX = 'v2/datapoint'
    _INGEST_ENDPOINT_EVENT_SUFFIX = 'v2/event'

    _QUEUE_STOP = object()

    def __init__(self, token, endpoint=DEFAULT_INGEST_ENDPOINT,
                 timeout=DEFAULT_TIMEOUT, batch_size=DEFAULT_BATCH_SIZE,
                 user_agents=None):
        self._token = token
        self._endpoint = endpoint.rstrip('/')
        self._timeout = timeout
        self._batch_size = max(1, batch_size)

        self._extra_dimensions = {}

        self._queue = queue.Queue()
        self._thread_running = False
        self._lock = threading.Lock()

        user_agent = ['{0}/{1}'.format(version.name, version.version)]
        if type(user_agents) == list:
            user_agent.extend(user_agents)

        self._session = requests.Session()
        self._session.headers.update({
            'X-SF-Token': self._token,
            'User-Agent': ' '.join(user_agent),
        })

    def _add_to_queue(self, metric_type, datapoint):
        raise NotImplementedError('Subclasses should implement this!')

    def _add_extra_dimensions(self, datapoint):
        with self._lock:
            if not self._extra_dimensions:
                return
            if datapoint.get('dimensions') is not None:
                datapoint['dimensions'].update(self._extra_dimensions)
            else:
                datapoint['dimensions'] = self._extra_dimensions

    def add_dimensions(self, dimensions):
        """Add one or more dimensions that will be included with every
        datapoint and event sent to SignalFx.

        Args:
            dimensions (dict): A mapping of {dimension: value, ...} pairs.
        """
        with self._lock:
            self._extra_dimensions.update(dimensions)

    def remove_dimensions(self, dimension_names):
        """Removes extra dimensions added by the add_dimensions() function.
        Ignores dimension names that don't exist.

        Args:
            dimension_names (list): List of dimension names to remove.
        """
        with self._lock:
            for dimension in dimension_names:
                if dimension in self._extra_dimensions:
                    del self._extra_dimensions[dimension]

    def send(self, cumulative_counters=None, gauges=None, counters=None):
        """Send the given metrics to SignalFx.

        Args:
            cumulative_counters (list): a list of dictionaries representing the
                cumulative counters to report.
            gauges (list): a list of dictionaries representing the gauges to
                report.
            counters (list): a list of dictionaries representing the counters
                to report.
        """
        if not gauges and not cumulative_counters and not counters:
            return

        data = {
            'cumulative_counter': cumulative_counters,
            'gauge': gauges,
            'counter': counters,
        }
        logging.debug('Sending datapoints to SignalFx: %s', data)

        for metric_type, datapoints in data.items():
            if not datapoints:
                continue
            if not isinstance(datapoints, list):
                raise TypeError('Datapoints not of type list %s', datapoints)
            for datapoint in datapoints:
                self._add_extra_dimensions(datapoint)
                self._add_to_queue(metric_type, datapoint)

        # Ensure the sending thread is running.
        self._start_thread()

    def send_event(self, event_type, category=None, dimensions=None,
                   properties=None, timestamp=None):
        """Send an event to SignalFx.

        Args:
            event_type (string): the event type (name of the event time
                series).
            category (string): the category of the event.
            dimensions (dict): a map of event dimensions.
            properties (dict): a map of extra properties on that event.
            timestamp (float): timestamp when the event has occured
        """
        if category and category not in SUPPORTED_EVENT_CATEGORIES:
            raise ValueError('Event category is not one of the supported' +
                             'types: {' +
                             ', '.join(SUPPORTED_EVENT_CATEGORIES) + '}')

        data = {
            'eventType': event_type,
            'category': category,
            'dimensions': dimensions or {},
            'properties': properties or {},
            'timestamp': int(timestamp) if timestamp else None,
        }

        logging.debug('Sending event to SignalFx: %s', data)
        self._add_extra_dimensions(data)
        return self._send_event(event_data=data, url='{0}/{1}'.format(
            self._endpoint, self._INGEST_ENDPOINT_EVENT_SUFFIX),
            session=self._session)

    def _send_event(self, event_data=None, url=None, session=None):
        raise NotImplementedError('Subclasses should implement this!')

    def _start_thread(self):
        # Locking the variable that tracks the thread status
        # 'self._thread_running' to make it an atomic operation.
        with self._lock:
            if self._thread_running:
                return
            self._thread_running = True

        self._send_thread = threading.Thread(target=self._send,
                                             name=self._THREAD_NAME)
        self._send_thread.daemon = True
        self._send_thread.start()
        logging.debug('Thread %s started', self._THREAD_NAME)

    def stop(self, msg='Thread stopped'):
        """Stop send thread and flush points for a safe exit."""
        with self._lock:
            if not self._thread_running:
                return
            self._thread_running = False
        self._queue.put(_BaseSignalFxIngestClient._QUEUE_STOP)
        self._send_thread.join()
        logging.debug(msg)

    def _send(self):
        try:
            while self._thread_running or not self._queue.empty():
                tmp_dp = self._queue.get(True)
                if tmp_dp == _BaseSignalFxIngestClient._QUEUE_STOP:
                    break
                datapoints_list = [tmp_dp]
                while (not self._queue.empty() and
                       len(datapoints_list) < self._batch_size):
                    tmp_dp = self._queue.get()
                    if tmp_dp != _BaseSignalFxIngestClient._QUEUE_STOP:
                        datapoints_list.append(tmp_dp)
                try:
                    self._post(self._batch_data(datapoints_list),
                               '{0}/{1}'.format(
                                   self._endpoint,
                                   self._INGEST_ENDPOINT_DATAPOINT_SUFFIX))
                except:
                    logging.exception('Posting data to SignalFx failed.')
        except KeyboardInterrupt:
            self.stop(msg='Thread stopped by keyboard interrupt.')

    def _batch_data(self, datapoints_list):
        """Convert the given list of datapoints into a serialized string that
        can be send to the ingest endpoint. Subclasses must implement this to
        provide the serialization relevant to their implementation."""
        raise NotImplementedError('Subclasses should implement this!')

    def _post(self, data, url, session=None, timeout=None):
        session = session or self._session
        timeout = timeout or self._timeout
        logging.debug('Raw datastream being sent: %s', pprint.pformat(data))
        response = session.post(url, data=data, timeout=timeout)
        logging.debug('Sending to SignalFx %s (%d %s)',
                      'succeeded' if response.ok else 'failed',
                      response.status_code, response.text)


class ProtoBufSignalFxIngestClient(_BaseSignalFxIngestClient):
    """SignalFx Ingest API client that uses Protocol Buffers.

    This class presents the interfaces that handle the serialization of data
    using Protocol Buffers.
    """

    def __init__(self, token, **kwargs):
        if not sf_pbuf:
            raise AssertionError('Protocol Buffers are not installed')

        super(ProtoBufSignalFxIngestClient, self).__init__(token, **kwargs)
        self._session.headers.update({
            'Content-Type': 'application/x-protobuf'
        })

    def _add_to_queue(self, metric_type, datapoint):
        pbuf_dp = sf_pbuf.DataPoint()
        self._assign_value_type(pbuf_dp, datapoint['value'])
        pbuf_dp.metricType = getattr(sf_pbuf, metric_type.upper())
        pbuf_dp.metric = datapoint['metric']
        if datapoint.get('timestamp'):
            pbuf_dp.timestamp = int(datapoint['timestamp'])
        self._set_dimensions(
            pbuf_dp, datapoint.get('dimensions', {}))
        self._queue.put(pbuf_dp)

    def _set_dimensions(self, pbuf_obj, dimensions):
        if not isinstance(dimensions, dict):
            raise ValueError('Invalid dimensions {0}; must be a dict!'
                             .format(dimensions))
        for key, value in dimensions.items():
            dim = pbuf_obj.dimensions.add()
            dim.key = key
            dim.value = value

    def _set_event_properties(self, pbuf_obj, properties):
        if not isinstance(properties, dict):
            raise ValueError('Invalid dimensions {0}; must be a dict!'
                             .format(properties))
        for key, value in properties.items():
            prop = pbuf_obj.properties.add()
            prop.key = key
            self._assign_property_value(prop, value)

    def _assign_property_value(self, prop, value):
        if isinstance(value, int):
            prop.value.intValue = value
        elif isinstance(value, long):
            if value > 9223372036854775807:
                raise ValueError('Invalid Value ' + str(value) +
                                 ' exceeds maximum signed 64 bit integer' +
                                 ' (9223372036854775807)')
            prop.value.intValue = value
        elif isinstance(value, float):
            prop.value.doubleValue = value
        elif isinstance(value, str):
            prop.value.strValue = value
        elif isinstance(value, unicode):
            prop.value.strValue = value
        elif isinstance(value, bool):
            prop.value.boolValue = value
        else:
            raise ValueError('Invalid Value ' + str(value))

    def _assign_value_type(self, pbuf_dp, value):
        if isinstance(value, int):
            pbuf_dp.value.intValue = value
        elif isinstance(value, long):
            if value > 9223372036854775807:
                raise ValueError('Invalid Value ' + str(value) +
                                 ' exceeds maximum signed 64 bit integer' +
                                 ' (9223372036854775807)')
            pbuf_dp.value.intValue = value
        elif isinstance(value, float):
            pbuf_dp.value.doubleValue = value
        elif isinstance(value, str):
            pbuf_dp.value.strValue = value
        elif isinstance(value, unicode):
            pbuf_dp.value.strValue = value
        else:
            raise ValueError('Invalid Value ' + str(value))

    def _batch_data(self, datapoints_list):
        dpum = sf_pbuf.DataPointUploadMessage()
        dpum.datapoints.extend(datapoints_list)
        return dpum.SerializeToString()

    def _send_event(self, event_data=None, url=None, session=None):
        pbuf_event = self._create_event_protobuf_message(event_data)
        pbuf_eventum = sf_pbuf.EventUploadMessage()
        pbuf_eventum.events.extend([pbuf_event])
        return self._post(pbuf_eventum.SerializeToString(), url, session)

    def _create_event_protobuf_message(self, event_data=None):
        pbuf_event = sf_pbuf.Event()
        pbuf_event.eventType = event_data['eventType']
        self._set_dimensions(
            pbuf_event, event_data.get('dimensions', {}))
        self._set_event_properties(
            pbuf_event, event_data.get('properties', {}))
        if event_data.get('category'):
            pbuf_event.category = getattr(sf_pbuf,
                                          event_data['category'].upper())
        if event_data.get('timestamp'):
            pbuf_event.timestamp = event_data['timestamp']
        return pbuf_event


class JsonSignalFxIngestClient(_BaseSignalFxIngestClient):
    """SignalFx Ingest API client that uses JSON.

    This class presents the interfaces that handle the serialization of data
    using JSON.
    """

    def __init__(self, token, **kwargs):
        super(JsonSignalFxIngestClient, self).__init__(token, **kwargs)
        self._session.headers.update({
            'Content-Type': 'application/json',
        })

    def _add_to_queue(self, metric_type, datapoint):
        self._queue.put({metric_type: datapoint})

    def _batch_data(self, datapoints_list):
        datapoints = collections.defaultdict(list)
        for item in datapoints_list:
            item_keys = list(item.keys())
            datapoints[item_keys[0]].append(item[item_keys[0]])
        return json.dumps(datapoints)

    def _send_event(self, event_data=None, url=None, session=None):
        return self._post(json.dumps([event_data]), url, session)
