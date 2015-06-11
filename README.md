# Python client library for SignalFx

This is a programmatic interface in Python for SignalFx's metadata and
ingest APIs. It is meant to provide a base for communicating with
SignalFx APIs that can be easily leveraged by scripts and applications
to interact with SignalFx or report metric and event data to SignalFx.
It is also the base for metric reporters that integrate with common
Python-based metric collections tools or libraries.

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
