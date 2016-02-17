"""
Unit tests for SignalFx Python client library.
Meant to be run with pytest.

These are tests for metrics metadata and tags functionality.
The four basic operations are search, get, update, delete.
search and get use GET; update uses PUT; delete uses DELETE.

Sending datapoints and events use POST.
"""

# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

import mock
import sys
import os

# to ensure correct signalfx path is used
tests_path = os.path.dirname(os.path.abspath(__file__))
client_path = tests_path.replace('tests', '')
sys.path.insert(0, client_path)

import mock_http_methods
import signalfx

# not clear what the purpose of this one is
@mock.patch('signalfx.SignalFx._post', mock_http_methods.mock_post)
def test_post():
    s = signalfx.SignalFx('A')
    s._post('http', 'datadd')

@mock.patch('signalfx.SignalFx._get', mock_http_methods.mock_get)
def test_get_and_search():
    s = signalfx.SignalFx('A')
    s.get_metric_by_name('jvm.cpu.load')
    s.search_tags('is_it_there')

@mock.patch('signalfx.SignalFx._put', mock_http_methods.mock_put)
def test_update():
    s = signalfx.SignalFx('A')
    s.update_dimension('kkkkk', 'vvvvv')

@mock.patch('signalfx.SignalFx._delete', mock_http_methods.mock_delete)
def test_delete():
    s = signalfx.SignalFx('A')
    s.delete_tag('there')
    s.delete_tag('not_there')

def main():
    test_post(); print 'posted'
    test_get_and_search(); print 'got'
    test_update(); print 'put'
    test_delete(); print 'deleted'

if __name__ == '__main__':
    main()
