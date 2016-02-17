"""
For testing purposes, these will be used to mock out the
    _post, _get, _put, _delete methods of SignalFxClient

sample_responses.py sets the Response attributes that are used by SignalFxClient methods,
    namely status_code and _content
"""

import sample_responses

def mock_post(self, url, data, **kwargs):
    """
    Returns example responses
    Args:
        url (string): URL whose results to mock
        data (optional): data associated with request
    """
    return

def mock_get(self, url, **kwargs):
    """
    Returns example responses
    Args:
        url (string): URL whose results to mock

    Returns:
        the Response object

    """
    return sample_responses.GETS[url]



def mock_put(self, url, data, **kwargs):
    """
    Returns example responses
    Args:
        url (string): URL whose results to mock
        data (string): data associated with request

    Returns:
        the Response object

    """
    return sample_responses.PUTS[(url, data)]


def mock_delete(self, url, **kwargs):
    """
    Returns example responses
    Args:
        url (string): URL whose results to mock

    Returns:
        the Response object
    """
    return sample_responses.DELETES[url]