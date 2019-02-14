Python client library for SignalFx
==================================

This is a programmatic interface in Python for SignalFx's metadata and
ingest APIs. It is meant to provide a base for communicating with
SignalFx APIs that can be easily leveraged by scripts and applications
to interact with SignalFx or report metric and event data to SignalFx.
It is also the base for metric reporters that integrate with common
Python-based metric collections tools or libraries.

Installation
------------

To install with `pip`:

.. code::

    $ pip install signalfx

To install from source:

.. code::

    $ git clone https://github.com/signalfx/signalfx-python.git
    $ cd signalfx-python/
    $ pip install -e .

Usage
-----

This client library provides programmatic access to SignalFx's APIs:

* the data ingest API;
* the metadata REST API;
* the SignalFlow API.

You start by instantiating a ``signalfx.SignalFx()`` object, which then gives
you access to the API client that you want:

.. code:: python

    import signalfx

    sfx = signalfx.SignalFx(api_endpoint='https://api.{REALM}.signalfx.com',
            ingest_endpoint='https://ingest.{REALM}.signalfx.com',
            stream_endpoint='https://stream.{REALM}.signalfx.com')


    # For the ingest API
    ingest = sfx.ingest('ORG_TOKEN')

    # For the REST API
    rest = sfx.rest('API_TOKEN')

    # For the SignalFlow API
    flow = sfx.signalflow('ACCESS_TOKEN')

If no endpoints are set manually, this library uses the ``us0`` realm by default. 
If you are not in this realm, you will need to explicitly set the
endpoint urls above. To determine if you are in a different realm and need to
explicitly set the endpoints, check your profile page in the SignalFx 
web application. You will also need to specify an access token when requesting
one of those clients. For the ingest client, you need to specify your
organization access token (which can be obtained from the
SignalFx organization you want to report data into). For the REST API,
you must use your user access token. For the SignalFlow client, either an
organization access token or a user access token may be used. For more
information on access tokens, see the API's `Authentication documentation`_.

.. _Authentication documentation: https://developers.signalfx.com/basics/authentication.html

Reporting data
~~~~~~~~~~~~~~

Basic usage of the library for reporting data goes as follows:

.. code:: python

    import signalfx

    with signalfx.SignalFx().ingest('ORG_TOKEN') as sfx:
        sfx.send(
            gauges=[
              {'metric': 'myfunc.time',
               'value': 532,
               'timestamp': 1442960607000},
              ...
            ],
            counters=[
              {'metric': 'myfunc.calls',
               'value': 42,
               'timestamp': 1442960607000},
              ...
            ],
            cumulative_counters=[
              {'metric': 'myfunc.calls_cumulative',
               'value': 10,
               'timestamp': 1442960607000},
              ...
            ])

If you're sending data from multiple places in your code, you should create
your ingest client once and use it throughout your application. Each ingest
client instance has an internal queue of datapoints and events that need to be
sent to SignalFx, as well as an internal thread draining that queue. **When you
no longer need the client instance, make sure you call** ``.stop()`` **on it to
ensure the queue is fully drained.**

.. code:: python

    import signalfx

    sfx = signalfx.SignalFx().ingest('ORG_TOKEN')
    try:
        sfx.send(...)
        sfx.send(...)
    finally:
        # Make sure that everything gets sent.
        sfx.stop()

The ``timestamp`` must be a millisecond precision timestamp; the number of
milliseconds elapsed since Epoch. The ``timestamp`` field is optional, but
strongly recommended. If not specified, it will be set by SignalFx's ingest
servers automatically; in this situation, the timestamp of your datapoints will
not accurately represent the time of their measurement (network latency,
batching, etc. will all impact when those datapoints actually make it to
SignalFx).

When sending datapoints with multiple calls to ``send()``, it is recommended to
re-use the same SignalFx client object for each ``send()`` call.

If you must use multiple client objects for the same token, which is not
recommended, it is important to call ``stop()`` after making all ``send()``
calls. Each SignalFx client object uses a background thread to send datapoints
without blocking the caller. Calling ``stop()`` will gracefully flush the
thread's send queue and close its TCP connections.

Sending multi-dimensional data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Reporting dimensions for the data is also optional, and can be accomplished by
specifying a ``dimensions`` parameter on each datapoint containing a dictionary
of string to string key/value pairs representing the dimensions:

.. code:: python

    import signalfx

    with signalfx.SignalFx().ingest('ORG_TOKEN') as sfx:
        sfx.send(
            gauges=[
              {
                'metric': 'myfunc.time',
                'value': 532,
                'timestamp': 1442960607000,
                'dimensions': {'host': 'server1', 'host_ip': '1.2.3.4'}
              },
              ...
            ], ...)

See `examples/generic_usecase.py`_ for a complete code sample showing how to
send data to SignalFx.

.. _examples/generic_usecase.py: examples/generic_usecase.py

Sending events
~~~~~~~~~~~~~~

Events can be sent to SignalFx via the ``send_event()`` function. The event
type must be specified, and dimensions and extra event properties can be
supplied as well.

.. code:: python

    import signalfx

    with signalfx.SignalFx().ingest('ORG_TOKEN') as sfx:
        sfx.send_event(
            event_type='deployments',
            dimensions={
                'host': 'myhost',
                'service': 'myservice',
                'instance': 'myinstance'},
            properties={
                'version': '2015.04.29-01'})

Metric metadata and tags
~~~~~~~~~~~~~~~~~~~~~~~~

The library includes functions to search, retrieve, and update metric
metadata and tags. Deleting tags is also supported.

.. code:: python

    import signalfx

    with signalfx.SignalFx().rest('ORG_TOKEN') as sfx:
        sfx.update_tag('tag_name',
                       description='An example tag',
                       custom_properties={'version': 'some_number'})

AWS integration
~~~~~~~~~~~~~~~

Optionally, the client may be configured to append additional dimensions to all
metrics and events sent to SignalFx. One use case for this is to append the AWS
unique ID of the current host as an extra dimension. For example,

.. code:: python

    import signalfx
    from signalfx.aws import AWS_ID_DIMENSION, get_aws_unique_id

    sfx = signalfx.SignalFx().ingest('ORG_TOKEN')

    # This dimension will be added to all datapoints sent.
    sfx.add_dimensions({AWS_ID_DIMENSION: get_aws_unique_id()})

    try:
        sfx.send(
            gauges=[
              {
                'metric': 'myfunc.time',
                'value': 532,
                'timestamp': 1442960607000
                'dimensions': {'host': 'server1', 'host_ip': '1.2.3.4'}
              },
            ])
    finally:
        sfx.stop()

Pyformance reporter
~~~~~~~~~~~~~~~~~~~

``pyformance`` is a Python library that provides CodaHale-style metrics in a
very Pythonic way. We offer a reporter that can report the ``pyformance``
metric registry data directly to SignalFx.

.. code:: python

    from signalfx.pyformance import (count_calls, count_calls_with_dims,
                                     gauge, SignalFxReporter)

    @count_calls
    def callme():
        # whatever
        pass
    
    @count_calls_with_dims(dimension_key="dimension_value")
    def callme_with_dims():
        # whatever
        pass

    sfx = SignalFxReporter(token='ORG_TOKEN')
    sfx.start()

    callme()
    callme()
    callme_with_dims()
    callme_with_dims()
    gauge('test').set_value(42)

See `examples/pyformance_usecase.py`_ for a complete code example using Pyformance.

.. _examples/pyformance_usecase.py: examples/pyformance_usecase.py

Executing SignalFlow computations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

SignalFlow is SignalFx's real-time analytics computation language. The
SignalFlow API allows SignalFx users to execute real-time streaming analytics
computations on the SignalFx platform. For more information, head over to our
Developers documentation:

* `SignalFlow Overview`_
* `Getting started with the SignalFlow API`_

.. _SignalFlow Overview: https://developers.signalfx.com/signalflow_analytics/signalflow_overview.html
.. _SignalFlow API Reference: https://developers.signalfx.com/signalflow_reference.html 

The SignalFlow client accepts either an Organization Access Token or a User API Token.
Executing a SignalFlow program is very simple with this client library:

.. code:: python

    import signalfx

    program = "data('cpu.utilization').mean().publish()"
    with signalfx.SignalFx().signalflow('ACCESS_TOKEN') as flow:
        print('Executing {0} ...'.format(program))
        computation = flow.execute(program)
        for msg in computation.stream():
            if isinstance(msg, signalfx.signalflow.messages.DataMessage):
                print('{0}: {1}'.format(msg.logical_timestamp_ms, msg.data))
            if isinstance(msg, signalfx.signalflow.messages.EventMessage):
                print('{0}: {1}'.format(msg.timestamp_ms, msg.properties))

Metadata about the streamed timeseries is received from ``.stream()``, but it
is automatically intercepted by the client library and made available through
the ``Computation`` object returned by ``execute()``:

.. code:: python

    if isinstance(msg, signalfx.signalflow.messages.DataMessage):
        for tsid, value in msg.data.items():
            metadata = computation.get_metadata(tsid)
            # Display metadata and datapoint value as desired

For more examples of how to execute SignalFlow computation with this library,
interpret and use the returned stream messages, you can look at the simple
example in `examples/signalflow/basic.py` or at the `SignalFlow CLI`_ and its
implementation which uses this library.

.. _examples/signalflow/basic.py: examples/signalflow/basic.py
.. _SignalFlow CLI: https://github.com/signalfx/signalflow-cli

Building a Pandas DataFrame from SignalFlow output
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

With the SignalFlow output being programmatically accessible, it's easy to
convert this data into any form that you need for further use or analysis. One
such use case is to build a `Pandas DataFrame`_ with the computation's output.
For a complete example of how to do this, see
`examples/signalflow/dataframe.py`.

.. _examples/signalflow/dataframe.py: examples/signalflow/dataframe.py
.. _Pandas DataFrame: http://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.html

Known Issues
------------

Sending only 1 datapoint and not seeing it in the chart
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The reason you are not seeing the metrics in the chart is because the script
that is calling the Python client module is exiting right after calling the
send method. The Python client library is mainly targeted towards sending a
continuous stream of metrics and was implemented to be asynchronous.

To work around this problem (most common in short-lived scripts for example),
register an ``atexit`` function to cleanly stop the datapoint sending thread
when your program exits:

.. code:: python

    import atexit
    import signalfx

    sfx = signalfx.SignalFx().ingest('ORG_TOKEN')
    atexit.register(sfx.stop)

SSLError when working with tags, metrics, dimensions, metrictimeseries, organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code::

    ERROR:root:Posting to SignalFx failed.
    SSLError: hostname 'api.signalfx.com' doesn't match either of '*.signalfuse.com', 'signalfuse.com'.

Root Cause: SignalFx's API endpoints (``api.signalfx.com``,
``ingest.signalfx.com`` and ``stream.signalfx.com``) have SSL SNI enabled and
the ``urllib3`` module in Python versions prior to 2.7.8 had a bug that causes
the above issue. This was fixed in later versions of Python; we recommend using
Python 2.7.9 or newer when using this library.

Exceeding int64 integer sizes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The protocol buffer used to transmit data through the ingest API restricts
integers and longs to (``-(2**63)`` to ``(2**63)-1``).  ``long`` values in
Python 2.x and ``int`` values in 3.x can exceed these values.  Any value or
property value less than ``-(2**63)`` or greater than ``(2**63)-1`` will raise
a ``ValueError`` exception.

License
-------

Apache Software License v2. Copyright © 2014-2017 SignalFx
