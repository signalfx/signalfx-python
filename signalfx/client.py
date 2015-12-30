# Copyright (C) 2015 SignalFx, Inc. All rights reserved.

import collections
import json
import logging
import pprint
import Queue
import requests
import threading

import version
from constants import DEFAULT_INGEST_ENDPOINT, DEFAULT_TIMEOUT, \
    DEFAULT_BATCH_SIZE, JSON_HEADER_CONTENT_TYPE, \
    PROTOBUF_HEADER_CONTENT_TYPE, SUPPORTED_EVENT_CATEGORIES

try:
    import generated_protocol_buffers.signal_fx_protocol_buffers_pb2 as sf_pbuf
except ImportError:
    sf_pbuf = None


class BaseSignalFx(object):

    def __init__(self, api_token, ingest_endpoint=DEFAULT_INGEST_ENDPOINT,
                 api_endpoint=None, timeout=DEFAULT_TIMEOUT,
                 batch_size=DEFAULT_BATCH_SIZE, user_agents=None):
        self._api_token = api_token
        self._ingest_endpoint = ingest_endpoint.rstrip('/')
        self._timeout = timeout
        self._batch_size = max(1, batch_size)
        if user_agents is None:
            user_agents = []
        self._user_agents = user_agents

    def send(self, cumulative_counters=None, gauges=None, counters=None):
        if not gauges and not cumulative_counters and not counters:
            return None
        data = {
            'cumulative_counter': cumulative_counters,
            'gauge': gauges,
            'counter': counters,
        }
        logging.debug('Sending datapoints to SignalFx: %s', data)
        return data

    def send_event(self, event_type, category=None, dimensions=None,
                   properties=None, timestamp=None):
        if timestamp:
            timestamp = int(timestamp)
        if category and category not in SUPPORTED_EVENT_CATEGORIES:
            raise ValueError('Event category is not one of the supported' +
                             'types: {' +
                             ', '.join(SUPPORTED_EVENT_CATEGORIES) + '}')
        data = {
            'category': category,
            'eventType': event_type,
            'dimensions': dimensions or {},
            'properties': properties or {},
            'timestamp': timestamp,
        }
        logging.debug('Sending event to SignalFx: %s', data)
        return data


class SignalFxClient(BaseSignalFx):
    """SignalFx API client.

    This class presents a programmatic interface to SignalFx's metadata and
    ingest APIs. At the time being, only ingest is supported; more will come
    later.
    """
    _HEADER_API_TOKEN_KEY = 'X-SF-Token'
    _HEADER_USER_AGENT_KEY = 'User-Agent'
    _INGEST_ENDPOINT_DATAPOINT_SUFFIX = 'v2/datapoint'
    _INGEST_ENDPOINT_EVENT_SUFFIX = 'v2/event'
    _THREAD_NAME = 'SignalFxDatapointSendThread'

    def __init__(self, api_token, **kwargs):
        super(SignalFxClient, self).__init__(api_token, **kwargs)
        self._ingest_session = self._prepare_ingest_session()
        self._queue = Queue.Queue()
        self.queue_stop_signal = SignalFxClient.QueueStopSignal()
        self._thread_running = False
        self._lock = threading.Lock()
        self._extra_dimensions = {}

    class QueueStopSignal(object):
        pass

    def _add_user_agents(self, session):
        # Adding user agent for the SignalFx Library Module
        session.headers[self._HEADER_USER_AGENT_KEY] +=\
            ' {name}/{version}'.format(
                name=version.name, version=version.version)
        # Adding custom user agents passed by client modules
        if self._user_agents:
            session.headers[self._HEADER_USER_AGENT_KEY] +=\
                ' {}'.format(' '.join(self._user_agents))

    def _add_header_api_token(self, session):
        session.headers.update({self._HEADER_API_TOKEN_KEY: self._api_token})

    def _prepare_base_session(self):
        session = requests.Session()
        self._add_user_agents(session)
        self._add_header_api_token(session)
        return session

    def _add_header_content_type(self, session):
        raise NotImplementedError('Subclasses should implement this!')

    def _prepare_ingest_session(self):
        session = self._prepare_base_session()
        self._add_header_content_type(session)
        return session

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
        data = super(SignalFxClient, self).send(
            cumulative_counters=cumulative_counters, gauges=gauges,
            counters=counters)
        if not data:
            return None
        for metric_type, datapoints in data.iteritems():
            if not datapoints:
                continue
            if not isinstance(datapoints, list):
                raise TypeError('Datapoints not of type list %s', datapoints)
            for datapoint in datapoints:
                self._add_extra_dimensions(datapoint)
                self._add_to_queue(metric_type, datapoint)
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
        data = super(SignalFxClient, self).send_event(
            event_type, category=category, dimensions=dimensions,
            properties=properties, timestamp=timestamp)
        if not data:
            return None
        self._add_extra_dimensions(data)
        return self._send_event(event_data=data, url='{0}/{1}'.format(
            self._ingest_endpoint, self._INGEST_ENDPOINT_EVENT_SUFFIX),
            session=self._ingest_session)

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
        self._thread_running = False
        self._queue.put(self.queue_stop_signal)
        self._send_thread.join()
        logging.debug(msg)

    def _send(self):
        try:
            while self._thread_running:
                tmp_dp = self._queue.get(True)
                if tmp_dp == self.queue_stop_signal:
                    break
                datapoints_list = [tmp_dp]
                while (not self._queue.empty() and
                       len(datapoints_list) < self._batch_size):
                    tmp_dp = self._queue.get()
                    if tmp_dp != self.queue_stop_signal:
                        datapoints_list.append(self._queue.get())
                self._post(self._batch_data(datapoints_list), '{0}/{1}'.format(
                    self._ingest_endpoint,
                    self._INGEST_ENDPOINT_DATAPOINT_SUFFIX))
        except KeyboardInterrupt:
            self.stop(msg='Thread stopped by keyboard interrupt.')

    def _batch_data(self, datapoints_list):
        raise NotImplementedError('Subclasses should implement this!')

    def _post(self, data, url, session=None):
        _session = session or self._ingest_session
        if logging.getLogger().isEnabledFor(logging.DEBUG):
            logging.debug(
                'Raw datastream being sent: %s', pprint.pformat(data))
        try:
            response = _session.post(url, data=data, timeout=self._timeout)
            logging.debug('Sending to SignalFx %s (%d %s)',
                          'succeeded' if response.ok else 'failed',
                          response.status_code, response.text)
        except Exception:
            logging.exception('Posting to SignalFx failed.')


class ProtoBufSignalFx(SignalFxClient):
    """SignalFx API client data handler that uses Protocol Buffers.

    This class presents the interfaces that handle the serialization of data
    using Protocol Buffers. Use the SignalFx class directly if you're not sure
    what's best for you here.
    """

    def __init__(self, api_token, **kwargs):
        super(ProtoBufSignalFx, self).__init__(api_token, **kwargs)
        if not sf_pbuf:
            raise AssertionError('Protocol Buffers are not installed')

    def _add_header_content_type(self, session):
        session.headers.update(PROTOBUF_HEADER_CONTENT_TYPE)

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
        elif isinstance(value, str):
            prop.value.strValue = value
        elif isinstance(value, float):
            prop.value.doubleValue = value
        elif isinstance(value, bool):
            prop.value.boolValue = value
        else:
            raise ValueError('Invalid Value ' + str(value))

    def _assign_value_type(self, pbuf_dp, value):
        if isinstance(value, int):
            pbuf_dp.value.intValue = value
        elif isinstance(value, str):
            pbuf_dp.value.strValue = value
        elif isinstance(value, float):
            pbuf_dp.value.doubleValue = value
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


class JsonSignalFx(SignalFxClient):
    """SignalFx API client data handler that uses Json.

    This class presents the interfaces that handle the serialization of data
    using Json. Use the SignalFx class directly if you're not sure what's best
    for you here.
    """

    def __init__(self, api_token, **kwargs):
        super(JsonSignalFx, self).__init__(api_token, **kwargs)

    def _add_header_content_type(self, session):
        session.headers.update(JSON_HEADER_CONTENT_TYPE)

    def _add_to_queue(self, metric_type, datapoint):
        self._queue.put({metric_type: datapoint})

    def _batch_data(self, datapoints_list):
        datapoints = collections.defaultdict(list)
        for item in datapoints_list:
            datapoints[item.keys()[0]].append(item[item.keys()[0]])
        return json.dumps(datapoints)

    def _send_event(self, event_data=None, url=None, session=None):
        return self._post(json.dumps([event_data]), url, session)
