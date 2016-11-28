# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import logging
import pprint
import requests

from . import constants, version

# TODO: this file needs rework. We want the REST API client to expose the same
# object abstractions as the API itself, with functions to manipulate those,
# instead of a disorderly bag of utility functions.


class SignalFxRestClient(object):
    """SignalFx REST API client."""

    _METRIC_ENDPOINT_SUFFIX = 'v2/metric'
    _DIMENSION_ENDPOINT_SUFFIX = 'v2/dimension'
    _DETECTOR_ENDPOINT_SUFFIX = 'v2/detector'
    _MTS_ENDPOINT_SUFFIX = 'v2/metrictimeseries'
    _TAG_ENDPOINT_SUFFIX = 'v2/tag'
    _ORGANIZATION_ENDPOINT_SUFFIX = 'v2/organization'

    def __init__(self, token, endpoint=constants.DEFAULT_API_ENDPOINT,
                 timeout=constants.DEFAULT_TIMEOUT):
        self._token = token
        self._endpoint = endpoint
        self._timeout = timeout

        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'X-SF-Token': self._token,
            'User-Agent': '{0}/{1}'.format(version.name, version.version),
        })

    def _u(self, *args):
        return '{0}/{1}'.format(self._endpoint, '/'.join(args))

    def _get(self, url, params=None, session=None, timeout=None):
        session = session or self._session
        timeout = timeout or self._timeout
        logging.debug('URL being retrieved: %s (params: %s)',
                      pprint.pformat(url), params)
        response = session.get(url, timeout=timeout, params=params)
        logging.debug('Getting from SignalFx %s (%d %s)',
                      'succeeded' if response.ok else 'failed',
                      response.status_code, response.text)
        return response

    def _put(self, url, data, session=None, timeout=None):
        session = session or self._session
        timeout = timeout or self._timeout
        logging.debug('Raw datastream being sent: %s', pprint.pformat(data))
        response = session.put(url, json=data, timeout=timeout)
        logging.debug('Putting to SignalFx %s (%d %s)',
                      'succeeded' if response.ok else 'failed',
                      response.status_code, response.text)
        return response

    def _post(self, url, data, session=None, timeout=None):
        session = session or self._session
        timeout = timeout or self._timeout
        logging.debug('Raw datastream being sent: %s', pprint.pformat(data))
        response = session.post(url, json=data, timeout=timeout)
        logging.debug('Posting to SignalFx %s (%d %s)',
                      'succeeded' if response.ok else 'failed',
                      response.status_code, response.text)
        return response

    def _delete(self, url, session=None, timeout=None):
        session = session or self._session
        timeout = timeout or self._timeout
        logging.debug('url associated with delete request: %s',
                      pprint.pformat(url))
        response = session.delete(url, timeout=timeout)
        logging.debug('Deleting from SignalFx %s (%d %s)',
                      'succeeded' if response.ok else 'failed',
                      response.status_code, response.text)
        return response

    def _search_metrics_and_metadata(self, metadata_endpoint, query,
                                     order_by=None, offset=None,
                                     limit=None, timeout=None):
        """
        generic function for elasticsearch queries; can search metrics,
            dimensions, metrictimeseries by changing metadata_endpoint
        Args:
            metadata_endpoint (string): API endpoint suffix (e.g. 'v2/metric')
            query (string): elasticsearch string query
            order_by (optional[string]): property by which to order results
            offset (optional[int]): number of results to skip for pagination
                (default=0)
            limit (optional[int]): how many results to return (default=50)
            timeout (optional[int]): how long to wait for response (in seconds)

        Returns:
            dictionary of query result
        """
        logging.debug('Performing an elasticsearch for %(qry)s at %(pt)s',
                      {'qry': query, 'pt': metadata_endpoint})
        url_to_get = '{0}?query={1}'.format(self._u(metadata_endpoint), query)
        if order_by is not None:
            url_to_get += '&orderBy=' + order_by
        # for offset and limit, use API defaults (by leaving them out of url)
        if offset is not None:
            url_to_get += '&offset=' + str(offset)
        if limit is not None:
            url_to_get += '&limit=' + str(limit)
        timeout = timeout or self._timeout
        resp = self._get(url_to_get, session=self._session, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    def _get_object_by_name(self, object_endpoint, object_name, timeout=None):
        """
        generic function to get object (metadata, tag, ) by name from SignalFx.

        Args:
            object_endpoint (string): API endpoint suffix (e.g. 'v2/tag')
            object_name (string): name of the object (e.g. 'jvm.cpu.load')

        Returns:
            dictionary of response
        """
        timeout = timeout or self._timeout
        resp = self._get(self._u(object_endpoint, object_name),
                         session=self._session, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    # functionality related to metrics
    def search_metrics(self, *args, **kwargs):
        """
        Args:
            query (string): elasticsearch string query
            order_by (optional[string]): property by which to order results
            offset (optional[int]): number of results to skip for pagination
                (default=0)
            limit (optional[int]): how many results to return (default=50)
            timeout (optional[int]): how long to wait for response (in seconds)

        Returns:
            result of query search on metrics
        """
        return self._search_metrics_and_metadata(
            self._METRIC_ENDPOINT_SUFFIX, *args, **kwargs)

    def get_metric_by_name(self, metric_name, **kwargs):
        """
        get a metric by name

        Args:
            metric_name (string): name of metric

        Returns:
            dictionary of response
        """
        return self._get_object_by_name(self._METRIC_ENDPOINT_SUFFIX,
                                        metric_name,
                                        **kwargs)

    def update_metric_by_name(self, metric_name, metric_type, description=None,
                              custom_properties=None, tags=None, **kwargs):
        """
        Create or update a metric object

        Args:
            metric_name (string): name of metric
            type (string): metric type, must be one of 'gauge', 'counter',
                            'cumulative_counter'
            description (optional[string]): a description
            custom_properties (optional[dict]): dictionary of custom properties
            tags (optional[list of strings]): list of tags associated with
                metric
        """
        data = {'type': metric_type.upper(),
                'description': description or '',
                'customProperties': custom_properties or {},
                'tags': tags or []}
        resp = self._put(self._u(self._METRIC_ENDPOINT_SUFFIX,
                                 str(metric_name)),
                         data=data, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # functionality related to dimensions
    def search_dimensions(self, *args, **kwargs):
        """
        Args:
            query (string): elasticsearch string query
            order_by (optional[string]): property by which to order results
            offset (optional[int]): number of results to skip for pagination
                (default=0)
            limit (optional[int]): how many results to return (default=50)
            timeout (optional[int]): how long to wait for response (in seconds)

        Returns:
            result of query search on dimensions
        """
        return self._search_metrics_and_metadata(
            self._DIMENSION_ENDPOINT_SUFFIX, *args, **kwargs)

    def get_dimension(self, key, value, **kwargs):
        """
        get a dimension by key and value

        Args:
            key (string): key of the dimension
            value (string): value of the dimension

        Returns:
            dictionary of response
        """
        return self._get_object_by_name(self._DIMENSION_ENDPOINT_SUFFIX,
                                        '{0}/{1}'.format(key, value),
                                        **kwargs)

    def update_dimension(self, key, value, description=None,
                         custom_properties=None, tags=None, **kwargs):
        """
        update a dimension
        Args:
            key (string): key of the dimension
            value (string): value of the dimension
            description (optional[string]): a description
            custom_properties (optional[dict]): dictionary of custom properties
            tags (optional[list of strings]): list of tags associated with
                metric
        """
        data = {'description': description or '',
                'customProperties': custom_properties or {},
                'tags': tags or [],
                'key': key,
                'value': value}
        resp = self._put(self._u(self._DIMENSION_ENDPOINT_SUFFIX, key, value),
                         data=data, **kwargs)
        resp.raise_for_status()
        return resp.json()

    # functionality related to metrictimeseries
    def search_metric_time_series(self, *args, **kwargs):
        """
        Args:
            query (string): elasticsearch string query
            order_by (optional[string]): property by which to order results
            offset (optional[int]): number of results to skip for pagination
                (default=0)
            limit (optional[int]): how many results to return (default=50)
            timeout (optional[int]): how long to wait for response (in seconds)

        Returns:
            result of query search on metric time series

        """
        return self._search_metrics_and_metadata(self._MTS_ENDPOINT_SUFFIX,
                                                 *args, **kwargs)

    def get_metric_time_series(self, mts_id, **kwargs):
        """get a metric time series by id"""
        return self._get_object_by_name(self._MTS_ENDPOINT_SUFFIX,
                                        mts_id,
                                        **kwargs)

    # functionality related to tags
    def search_tags(self, *args, **kwargs):
        """
        Args:
            query (string): elasticsearch string query
            order_by (optional[string]): property by which to order results
            offset (optional[int]): number of results to skip for pagination
                (default=0)
            limit (optional[int]): how many results to return (default=50)
            timeout (optional[int]): how long to wait for response (in seconds)

        Returns:
            result of query search on tags

        """
        return self._search_metrics_and_metadata(self._TAG_ENDPOINT_SUFFIX,
                                                 *args, **kwargs)

    def get_tag(self, tag_name, **kwargs):
        """get a tag by name

        Args:
            tag_name (string): name of tag to get

        Returns:
            dictionary of the response

        """
        return self._get_object_by_name(self._TAG_ENDPOINT_SUFFIX,
                                        tag_name,
                                        **kwargs)

    def update_tag(self, tag_name, description=None,
                   custom_properties=None, **kwargs):
        """update a tag by name

        Args:
            tag_name (string): name of tag to update
            description (optional[string]): a description
            custom_properties (optional[dict]): dictionary of custom properties
        """
        data = {'description': description or '',
                'customProperties': custom_properties or {}}
        resp = self._put(self._u(self._TAG_ENDPOINT_SUFFIX, tag_name),
                         data=data, **kwargs)
        resp.raise_for_status()
        return resp.json()

    def delete_tag(self, tag_name, **kwargs):
        """delete a tag by name

        Args:
            tag_name (string): name of tag to delete
        """
        resp = self._delete(self._u(self._TAG_ENDPOINT_SUFFIX, tag_name),
                            **kwargs)
        resp.raise_for_status()
        # successful delete returns 204, which has no associated json
        return resp

    # functionality related to organizations (more to come)
    def get_organization(self, **kwargs):
        """Get the organization to which the user belongs

        Returns:
            dictionary of the response
        """
        resp = self._get(self._u(self._ORGANIZATION_ENDPOINT_SUFFIX),
                         **kwargs)
        resp.raise_for_status()
        return resp.json()

    # functionality related to detectors
    def get_detectors(self, offset=0, limit=100, **kwargs):
        detectors = []
        while True:
            resp = self._get(self._u(self._DETECTOR_ENDPOINT_SUFFIX),
                             params={'offset': offset, 'limit': limit},
                             **kwargs)
            resp.raise_for_status()
            data = resp.json()
            detectors += data['results']
            if len(detectors) == data['count']:
                break
            offset = len(detectors)
        return detectors

    def create_detector(self, detector):
        """Creates a new detector.

        Args:
            detector (object): the detector model object. Will be serialized as
                JSON.
        Returns:
            dictionary of the response (created detector model).
        """
        resp = self._post(self._u(self._DETECTOR_ENDPOINT_SUFFIX),
                          data=detector)
        resp.raise_for_status()
        return resp.json()

    def update_detector(self, detector_id, detector):
        """Update an existing detector.

        Args:
            detector_id (string): the ID of the detector.
            detector (object): the detector model object. Will be serialized as
                JSON.
        Returns:
            dictionary of the response (updated detector model).
        """
        resp = self._put(self._u(self._DETECTOR_ENDPOINT_SUFFIX, detector_id),
                         data=detector)
        resp.raise_for_status()
        return resp.json()

    def delete_detector(self, detector_id):
        """Remove a detector.

        Args:
            detector_id (string): the ID of the detector.
        """
        resp = self._delete(self._u(self._DETECTOR_ENDPOINT_SUFFIX,
                                    detector_id))
        resp.raise_for_status()
        # successful delete returns 204, which has no response json
        return resp
