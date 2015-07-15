# Python client library for SignalFx

This is a programmatic interface in Python for SignalFx's metadata and
ingest APIs. It is meant to provide a base for communicating with
SignalFx APIs that can be easily leveraged by scripts and applications
to interact with SignalFx or report metric and event data to SignalFx.
It is also the base for metric reporters that integrate with common
Python-based metric collections tools or libraries.


## Installation

```
pip install signalfx
```

## Usage

### API access token

To use this library, you need a SignalFx API access token, which can be
obtained from the SignalFx organization you want to report data into.

### Reporting data

The "raw" usage of the library for reporting data goes as follows:

```python
import signalfx

sfx = signalfx.SignalFx('MY_TOKEN')
sfx.send(
    gauges=[
      {'metric': 'myfunc.time', 'value': 532},
      ...
    ],
    counters=[
      {'metric': 'myfunc.calls', 'value': 42},
      ...
    ])
```

See `examples/generic_usecase.py` for a complete code example for Reporting data.

### Sending events

Events can be sent to SignalFx via the `send_event` function. The
event type must be specified, and dimensions and extra event properties
can be supplied as well.

```python
import signalfx

sfx = signalfx.SignalFx('MY_TOKEN')
sfx.send_event(
    event_type='deployments',
    dimensions={
        'host': 'myhost',
        'service': 'myservice',
        'instance': 'myinstance'},
    properties={
        'version': '2015.04.29-01'})
```

See `examples/generic_usecase.py` for a complete code example Sending events.

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

sfx = signalfx.pyformance.SignalFxReporter(api_token='MY_TOKEN')
sfx.start()

callme()
callme()
gauge('test').set_value(42)
...
```

See `examples/pyformance_usecase.py` for a complete code example using Pyformance.


## Known Issues

#### Sending only 1 datapoint and not seeing it in the chart.

Root Cause: The reason you are not seeing the metrics in the chart is because the script that is calling the python client module is exiting right after calling the send method. The python client library is mainly targeted towards sending a continuous stream of metrics and was implemented to be asynchronous.

Workaround:  Adding a sleep [eg: time.sleep(5)] for say 5 secs before exciting from your script or run your script from a python interpreter you should start seeing your metric in the chart. Or if you send a stream or metrics, you will see the metrics in the chart.?add


#### SSLError when sending events by calling send_event() method

```
ERROR:root:Posting to SignalFx failed.
SSLError: hostname 'api.signalfx.com' doesn't match either of '*.signalfuse.com', 'signalfuse.com'
```

Solution: Please upgrade to python version 2.7.8, 2.7.9 or 2.7.10.
