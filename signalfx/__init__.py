# Copyright (C) 2015 SignalFx, Inc. All rights reserved.

import collections
import json
import logging
import pprint
import Queue
import requests
from threading import Thread, Lock
import time

import version
_USE_PROTOCOL_BUFFERS = True
try:
    import generated_protocol_buffers.signal_fx_protocol_buffers_pb2 as sf_pbuf
except ImportError:
    logging.warn('Protocol Buffers not installed properly. Switching to Json.')
    _USE_PROTOCOL_BUFFERS = False

# Default Parameters
DEFAULT_API_ENDPOINT = 'https://api.signalfx.com'
DEFAULT_API_TIMEOUT_SEC = 1  # Timeout for the HTTP POST Calls
DEFAULT_BATCH_SIZE = 300  # Will wait for this many requests before posting
DEFAULT_INGEST_ENDPOINT = 'https://ingest.signalfx.com'

# Global Parameters
JSON_HEADER_CONTENT_TYPE = {'Content-Type': 'application/json'}
PROTOBUF_HEADER_CONTENT_TYPE = {'Content-Type': 'application/x-protobuf'}


class __BaseSignalFx(object):

    def __init__(self, api_token, batch_size=DEFAULT_BATCH_SIZE,
                 user_agents=[], timeout=DEFAULT_API_TIMEOUT_SEC,
                 ingest_endpoint=DEFAULT_INGEST_ENDPOINT,
                 api_endpoint=DEFAULT_API_ENDPOINT):
        self._api_token = api_token
        self._batch_size = max(1, batch_size)
        self._user_agents = user_agents
        self._timeout = timeout
        self._ingest_endpoint = ingest_endpoint.rstrip('/')
        self._api_endpoint = api_endpoint.rstrip('/')

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

    def send_event(self, event_type, dimensions=None, properties=None):
        data = {'eventType': event_type,
                'dimensions': dimensions or {},
                'properties': properties or {}}
        logging.debug('Sending event to SignalFx: %s', data)
        return data


SignalFxLoggingStub = __BaseSignalFx


class SignalFxClient(__BaseSignalFx):
    """SignalFx API client.

    This class presents a programmatic interface to SignalFx's metadata and
    ingest APIs. At the time being, only ingest is supported; more will come
    later.
    """
    _HEADER_API_TOKEN_KEY = 'X-SF-Token'
    _HEADER_USER_AGENT_KEY = 'User-Agent'
    _INGEST_ENDPOINT_SUFFIX = 'v2/datapoint'
    _API_ENDPOINT_SUFFIX = 'v1/event'
    _THREAD_NAME = 'SignalFxDatapointSendThread'

    def __init__(self, api_token, **kwargs):
        super(SignalFxClient, self).__init__(api_token, **kwargs)
        self._ingest_session = self._prepare_ingest_session()
        self._api_session = self._prepare_api_session()
        self._queue = Queue.Queue()
        self._thread_running = False
        self._send_thread = None
        self._lock = Lock()

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

    def _prepare_api_session(self):
        session = self._prepare_base_session()
        session.headers.update(JSON_HEADER_CONTENT_TYPE)
        return session

    def _add_to_queue(self, metric_type, datapoint):
        raise NotImplementedError('Subclasses should implement this!')

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
                self._add_to_queue(metric_type, datapoint)
        self._start_thread()

    def send_event(self, event_type, dimensions=None, properties=None):
        """Send an event to SignalFx.

        Args:
            event_type (string): the event type (name of the event time
                series).
            dimensions (dict): a map of event dimensions.
            properties (dict): a map of extra properties on that event.
        """
        data = super(SignalFxClient, self).send_event(
            event_type, dimensions=dimensions, properties=properties)
        if not data:
            return None
        return self._post(json.dumps(data), '{0}/{1}'.format(
            self._api_endpoint, self._API_ENDPOINT_SUFFIX),
            session=self._api_session,)

    def stop(self, force=False):
        """Sends all metrics in the pipeline to SignalFx
        and stops all threads.

        Args:
            force (boolean): Defaults to False. Will exit without flushing
            data if set to True.
        """
        logging.debug('Stop called with force=%s. Exiting %s sending '
                      'pending metrics (if any) to SignalFx', force, 'Without'
                      if force else 'After')
        if self._send_thread is None or force:
            return
        self._stop_thread()

    def _start_thread(self):
        # Locking the variable tha tracks the thread status
        # 'self._thread_running' to make it an atomic operation.
        _ = self._lock.acquire()
        if self._thread_running:
            self._lock.release()
            return
        self._thread_running = True
        self._lock.release()
        self._send_thread = Thread(target=self._send, name=self._THREAD_NAME)
        self._send_thread.daemon = True
        self._send_thread.start()
        logging.debug('Thread %s started', self._THREAD_NAME)

    def _stop_thread(self):
        while not self._queue.empty():  # Polling for the Queue to be empty
            time.sleep(1)
        _ = self._lock.acquire()
        self._thread_running = False
        self._lock.release()
        self._send_thread.join()
        logging.debug('Thread %s stopped', self._THREAD_NAME)

    def _send(self):
        while self._thread_running:
            datapoints_list = [self._queue.get(True)]
            while (not self._queue.empty() and
                    len(datapoints_list) < self._batch_size):
                datapoints_list.append(self._queue.get())
            self._post(self._batch_data(datapoints_list), '{0}/{1}'.format(
                self._ingest_endpoint, self._INGEST_ENDPOINT_SUFFIX))

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
    using Protocol Buffers
    """

    def __init__(self, api_token, **kwargs):
        super(ProtoBufSignalFx, self).__init__(api_token, **kwargs)

    def _add_header_content_type(self, session):
        session.headers.update(PROTOBUF_HEADER_CONTENT_TYPE)

    def _add_to_queue(self, metric_type, datapoint):
        pbuf_dp = sf_pbuf.DataPoint()
        self._assign_value_type(pbuf_dp, datapoint['value'])
        pbuf_dp.metricType = getattr(sf_pbuf, metric_type.upper())
        pbuf_dp.metric = datapoint['metric']
        if datapoint.get('timestamp'):
            pbuf_dp.timestamp = int(datapoint['timestamp'])
        self._set_datapoint_dimensions(
            pbuf_dp, datapoint.get('dimensions', {}))
        self._queue.put(pbuf_dp)

    def _set_datapoint_dimensions(self, pbuf_dp, dimensions):
        if not isinstance(dimensions, dict):
            raise ValueError('Invalid dimensions {0}; must be a dict!'
                             .format(dimensions))
        for key, value in dimensions.items():
            dim = pbuf_dp.dimensions.add()
            dim.key = key
            dim.value = value

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


class JsonSignalFx(SignalFxClient):
    """SignalFx API client data handler that uses Json.

    This class presents the interfaces that handle the serialization of data
    using Json
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


SignalFx = ProtoBufSignalFx if _USE_PROTOCOL_BUFFERS else JsonSignalFx
