# Python client library for SignalFx

This is a programmatic interface in Python for SignalFx's metadata and
ingest APIs. It is meant to provide a base for communicating with
SignalFx APIs that can be easily leveraged by scripts and applications
to interact with SignalFx or report metric and event data to SignalFx.
It is also the base for metric reporters that integrate with common
Python-based metric collections tools or libraries.

## Installation

To install from pip:

```
pip install signalfx
```

To install from source:

```
git clone https://github.com/signalfx/signalfx-python.git
cd signalfx-python
python setup.py install
```

## Usage

This client library provides programmatic access to SignalFx's APIs:

* the data ingest API;
* the metadata REST API;
* the SignalFlow API.

You start by instantiating a `signalfx.SignalFx()` object, which then
gives you access to the API client that you want:

```python
import signalfx

sfx = signalfx.SignalFx()

# For the ingest API
ingest = sfx.ingest('ORG_ACCESS_TOKEN')

# For the REST API
rest = sfx.rest('USER_ACCESS_TOKEN')

# For the SignalFlow API
flow = sfx.signalflow('USER_ACCESS_TOKEN')
```

As you may have noticed, you need to specify an access token when
requesting one of those clients. For the ingest client, you need to
specify your organization or team's API access token (which can be
obtained from the SignalFx organization you want to report data into).
For the REST API and SignalFlow API clients, you must use your user
access token. For more information on access tokens, see the API's
[Authentication Overview
documentation](https://developers.signalfx.com/docs/authentication-overview).

### Reporting data

Basic usage of the library for reporting data goes as follows:

```python
import signalfx

sfx = signalfx.SignalFx().ingest('MY_TOKEN')
try:
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
finally:
    # After all datapoints have been sent, flush any remaining messages
    # in the send queue and terminate all connections.
    sfx.stop()
```

The `timestamp` must be a millisecond precision timestamp; the number of
milliseconds elapsed since Epoch. The `timestamp` field is optional, but
strongly recommended. If not specified, it will be set by SignalFx's
ingest servers automatically; in this situation, the timestamp of your
datapoints will not accurately represent the time of their measurement
(network latency, batching, etc. will all impact when those datapoints
actually make it to SignalFx).

When sending datapoints with multiple calls to `send()`, it is recommended
to re-use the same SignalFx client object for each `send()` call.

If you must use multiple client objects for the same token, which is not
recommended, it is important to call `stop()` after making all `send()`
calls. Each SignalFx client object uses a background thread to send
datapoints without blocking the caller. Calling `stop()` will gracefully
flush the thread's send queue and close its TCP connections.

#### Sending multi-dimensional data

Reporting dimensions for the data is also optional, and can be
accomplished by specifying a `dimensions` parameter on each datapoint
containing a dictionary of string to string key/value pairs representing
the dimensions:

```python
import signalfx

sfx = signalfx.SignalFx().ingest('MY_TOKEN')
try:
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
finally:
    sfx.stop()
```

See [`examples/generic_usecase.py`](examples/generic_usecase.py) for a
complete code sample showing how to send data to SignalFx.

### Sending events

Events can be sent to SignalFx via the `send_event` function. The
event type must be specified, and dimensions and extra event properties
can be supplied as well.

```python
import signalfx

sfx = signalfx.SignalFx().ingest('MY_TOKEN')
try:
    sfx.send_event(
        event_type='deployments',
        dimensions={
            'host': 'myhost',
            'service': 'myservice',
            'instance': 'myinstance'},
        properties={
            'version': '2015.04.29-01'})
finally:
    sfx.stop()
```

See `examples/generic_usecase.py` for a complete code example.

### Metric metadata and tags

The library includes functions to search, retrieve, and update metric
metadata and tags. Deleting tags is also supported.

```python
import signalfx

sfx = signalfx.SignalFx().rest('MY_TOKEN')
sfx.update_tag('tag_name',
               description='An example tag',
               custom_properties={'version': 'some_number'})
```

### AWS integration

Optionally, the client may be configured to append additional dimensions to
all metrics and events sent to SignalFx. One use case for this is to append
the AWS unique ID of the current host as an extra dimension.
For example,

```python
import signalfx
from signalfx.aws import AWS_ID_DIMENSION, get_aws_unique_id

sfx = signalfx.SignalFx().ingest('MY_TOKEN')

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
```

### Pyformance reporter

`pyformance` is a Python library that provides CodaHale-style metrics in
a very Pythonic way. We offer a reporter that can report the
`pyformance` metric registry data directly to SignalFx.

```python
from pyformance import count_calls, gauge
import signalfx.pyformance

@count_calls
def callme():
    # whatever
    pass

sfx = signalfx.pyformance.SignalFxReporter(token='MY_TOKEN')
sfx.start()

callme()
callme()
gauge('test').set_value(42)
...
```

See `examples/pyformance_usecase.py` for a complete code example using
Pyformance.

### Executing SignalFlow computations

SignalFlow is SignalFx's real-time analytics computation language. The
SignalFlow API allows SignalFx users to execute real-time streaming
analytics computations on the SignalFx platform. For more information,
head over to our Developers documentation:

* [SignalFlow
  Overview](https://developers.signalfx.com/docs/signalflow-overview)
* [Getting started with the SignalFlow
  API](https://developers.signalfx.com/docs/getting-started-with-the-signalflow-api)

Executing a SignalFlow program is very simple with this client library:

```python
import signalfx

program = "data('cpu.utilization').mean().publish()"
flow = signalfx.SignalFx().signalflow('MY_TOKEN')
try:
    print('Executing {0} ...'.format(program))
    computation = flow.execute(program)
    for msg in computation.stream():
        if isinstance(msg, signalfx.signalflow.messages.DataMessage):
            print('{0}: {1}'.format(msg.logical_timestamp_ms, msg.data))
        if isinstance(msg, signalfx.signalflow.messages.EventMessage):
            print('{0}: {1}'.format(msg.timestamp_ms, msg.properties))
finally:
    flow.close()
```

Metadata about the streamed timeseries is automatically intercepted by
the client library and made available through the `Computation` object
returned by `execute()`:

```python
if isinstance(msg, signalfx.signalflow.messages.DataMessage):
    for datapoint in msg.data:
        tsid = datapoint['tsId']
        metadata = computation.get_metadata(tsid)
        value = datapoint['value']
        # Display metadata and datapoint value as desired
```

For more examples of how to execute SignalFlow computation with this
library, interpret and use the returned stream messages, you can look at
the [SignalFlow CLI](https://github.com/signalfx/signalflow-cli) and its
implementation which uses this library.

## Known Issues

### Sending only 1 datapoint and not seeing it in the chart

The reason you are not seeing the metrics in the chart is because the
script that is calling the Python client module is exiting right after
calling the send method. The Python client library is mainly targeted
towards sending a continuous stream of metrics and was implemented to be
asynchronous.

To work around this problem (most common in short-lived scripts for
example), register an `atexit` function to cleanly stop the datapoint
sending thread when your program exits:

```python
import atexit
import signalfx

sfx = signalfx.SignalFx().ingest('MY_TOKEN')
atexit.register(sfx.stop)
```

### SSLError when working with tags, metrics, dimensions, metrictimeseries, organization

```
ERROR:root:Posting to SignalFx failed.
SSLError: hostname 'api.signalfx.com' doesn't match either of
'*.signalfuse.com', 'signalfuse.com'.
```

Root Cause: SignalFx's API endpoint(api.signalfx.com) have SSL SNI enabled
and the `urllib3` module in Python versions prior to 2.7.8 had a bug
that causes the above issue. This was fixed in later versions of Python; we
recommend using Python 2.7.9 or newer when using this library.
