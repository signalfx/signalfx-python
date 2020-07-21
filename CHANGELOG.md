### CHANGELOG

This file documents important changes to the SignalFx Python client library.
- [[1.1.9] - 2020-07-21: Fix get_detector methods](#119---2020-07-21--fix-get_detector-methods)
- [[1.1.8] - 2020-07-20: Fix tests and connection errors](#118---2020-07-20--fix-tests-and-connection-errors)
- [[1.1.7] - 2020-06-17: Fix get data link](#117---2020-06-17-fix-get-data-link)
- [[1.1.6] - 2020-05-30: Fix JSON ingest client](#116---2020-05-30-fix-json-ingest-client)
- [[1.1.5] - 2020-04-27: Add datalink methods](#115---2020-04-27-add-datalink-methods)
- [[1.1.4] - 2020-03-25: Add ingest error counters](#114---2020-03-25-add-ingest-error-counters)
- [[1.1.3] - 2020-01-16: Add new dashboard methods](#113---2020-01-16-add-new-dashboard-methods)
- [[1.1.2] - 2019-11-14: Fix accessing some computation response fields](#112---2019-11-14-fix-accessing-some-computation-response-fields)
- [[1.1.1] - 2019-08-22: Expanded Detector methods and Computation messages](#111---2019-08-22-added-detector-event-method-and-computation-messages)
- [[1.1.0] - 2019-02-28: Expanded Detector and Incident methods](#110---2019-02-28-expanded-detector-and-incident-methods)
- [[1.0.19] - 2018-05-03: dimension support in pyformance wrapper](#1019---2018-05-03-dimension-support-in-pyformance-wrapper)
- [[1.0.18] - 2018-03-15: Compression of datapoint payloads](#1018---2018-03-15-compression-of-datapoint-payloads)
- [[1.0.17] - 2018-03-02: Support for immediate SignalFlow results](#1017---2018-03-02-support-for-immediate-signalflow-results)
- [[1.0.16] - 2017-03-24: SignalFlow streaming performance](#1016---2017-03-24-signalflow-streaming-performance)
- [[1.0.15] - 2017-02-21: Preflight API](#1015---2017-02-21-preflight-api)
- [[1.0.14] - 2016-12-07: SignalFlow client bug fixes and context managers](#1014---2016-12-07-signalflow-client-bug-fixes-and-context-managers)
- [[1.0.13] - 2016-12-05: More features from detector APIs](#1013---2016-12-05-more-features-from-detector-apis)
- [[1.0.12] - 2016-11-28: Detector APIs](#1012---2016-11-28-detector-apis)
- [[1.0.11] - 2016-11-23: Long value support](#1011---2016-11-23-long-value-support)
- [[1.0.10] - 2016-11-21: Unicode event properties fix](#1010---2016-11-21-unicode-event-properties-fix)
- [[1.0.9] - 2016-10-26: Datapoints queue draining fix](#109---2016-10-26-datapoints-queue-draining-fix)
- [[1.0.8] - 2016-10-20: A missing field from events](#108---2016-10-20-a-missing-field-from-events)
- [[1.0.7] - 2016-10-05: More Python 3 compatibility](#107---2016-10-05-more-python-3-compatibility)
- [[1.0.5] - 2016-09-29: Python 3 compatibility](#105---2016-09-29-python-3-compatibility)
- [[1.0.1] - 2016-06-02: Support for SignalFlow API](#101---2016-06-02-support-for-signalflow-api)

#### [1.1.9] - 2020-07-21: Fix get_detector methods

`get_detector_events` and `get_detector_incidents` failed to correctly pass named arguments.

#### [1.1.8] - 2020-07-20: Fix tests and connection errors

* Fix some broken tests and flake8 problems.
* Handle ConnectionErrors caused by faulty urllib3 [#104](https://github.com/signalfx/signalfx-python/pull/104)
* Add python version classifiers [#103](https://github.com/signalfx/signalfx-python/pull/103)
* Adjust `get_aws_unique_id` to try ECS metadata before EC2. [#71](https://github.com/signalfx/signalfx-python/pull/71)
* Add additional parameters to the client. [#105](https://github.com/signalfx/signalfx-python/pull/105)

#### [1.1.7] - 2020-06-17: Fix Get Data Link

The `get_datalink` function was just completely wrong and errored. Oops!

#### [1.1.6] - 2020-05-30: Fix JSON ingest client

Fix the JSON ingest client when using a Python 3.x interpreter. The `zlib`
module expects a `bytes` object passed to the `zlib.compress()` function, so we
need to encode our JSON payloads as UTF-8 byte strings before passing them to
the `_post()` function.

#### [1.1.5] - 2020-04-27: Add datalink methods

Adds `get_datalinks` and `get_datalink`.

#### [1.1.4] - 2020-03-25: Add ingest error counters

Adds counters for errors during ingest and `reset_error_counters` to reset and
return those counters.

#### [1.1.3] - 2020-01-16: Add new dashboard methods

Added `get_dashboards`, `get_dashboard_group`, and `get_dashboard_groups`.

#### [1.1.2] - 2019-11-14: Fix accessing some computation response fields

Fixed some bugs that tried to access a missing key

#### [1.1.1] - 2019-08-22: Added Detector Event method and Computation messages

* Added `get_detector_events` method for getting events for a detector.
* Added new properties for computation populated by job info messages

#### [1.1.0] - 2019-02-28: Expanded Detector and Incident methods

Added methods for accessing the API functionality of retrieving incidents,
retrieving a detector by its ID, retrieving incidents for a detector by its ID,
and clearing an incident by its ID.

Also added preliminary support for `disable_all_metric_publishes` flag when
executing SignalFlow computations and removed an unsupported `Property`
datapoint attribute.

#### [1.0.19] - 2018-05-03: Dimension support in Pyformance wrapper

This release enhances the SignalFx pyformance package and extends the Pyformance
registry to support dimensional metadata. Please refer to the README and
examples for more information on changes to the pyformance package.

#### [1.0.18] - 2018-03-15: Compression of datapoint payloads

The main change in 1.0.18 is that payloads of datapoints sent to SignalFx will
now be compressed by default (using GZip compression and `Content-Encoding:
gzip`). This can be disabled by specifying `compress=False` on the SignalFx
client, or on the ingest sub-client directly.

#### [1.0.17] - 2018-03-02: Support for immediate SignalFlow results

Added support for the new `immediate` flag when executing SignalFlow
computation. Setting this flag to `true` forces the system to shift the
timerange of the computation by the `maxDelay` amount (either detected, or
specified), to ensure that the computation returns and completes without
additional delay to wait for late data.

Also added support in the library to access event metadata on events received
from a SignalFlow computation.

Updated the default TCP timeout to 5 seconds to match our Java and Ruby
libraries.

#### [1.0.16] - 2017-03-24: SignalFlow streaming performance

Added support for compressed SignalFlow WebSocket messages, which improves the
streaming performance by reducing the bandwidth requirements of the client.

#### [1.0.15] - 2017-02-20: Preflight API

Added support for the detector preflighting API, allowing for the execution of a
detector program in a mode that simply summarizes the events that would
otherwise be generated, allowing for the quicker execution of that preflighting
over longer spans of historical data.

This release also includes a bugfix to how the total number of input timeseries
is calculated, as well as support for a new version of the binary data message
encoding (not yet used).

#### [1.0.14] - 2016-12-07: SignalFlow client bug fixes and context managers

Fixes a bug in the SignalFlow streaming computation client library that would
lead to an incomplete first data batch returned from the computation stream when
the program being executed as multiple published streams.

All three sub-clients also now support Python context managers so they can be
used in `with` blocks:

```python
with signalfx.SignalFx().signalflow('MY_TOKEN') as flow:
    computation = flow.execute(program)
    for msg in computation.stream():
        # ...
```

#### [1.0.13] - 2016-12-05: More features from detector APIs

Added support for the `/v2/detector/validate` endpoint via
`rest.validate_detector()`, and support for searching detectors by tags when
using `rest.get_detectors()`.

It is also now possible to pass `ignore_not_found=True` to REST delete
operations to ignore failures on attempting to remove a non-existent resource
for which the DELETE call would otherwise return a 404.

#### [1.0.12] - 2016-11-28: Detector APIs

Added support for managing SignalFlow V2 detectors via the REST client.

#### [1.0.11] - 2016-11-23: Long value support

`long` type metric values were previously unsupported.  This release allows
int64 values and property values as defined by the protocol buffer. Values
greater than or equal to `-(2**63)` and less than or equal to `(2**63)-1`.
Values exceeding the specified boundaries will raise a ``ValueError`` exception.

Boolean property values were previously dispatched as integer values. This
release fixes this and emits boolean property values as a boolean type.

#### [1.0.10] - 2016-11-21: Unicode event properties fix

Unicode strings were previously unsupported for event properties. This release
allows event properties to be assigned unicode strings.

#### [1.0.9] - 2016-10-26: Datapoints queue draining fix

In certain situations, it was possible for the ingest client to stop and let the
program exit before the datapoints queue was fully drained to SignalFx. This
release fixes this and ensures that the background sending thread does not
prematurely exits before the queue is fully drained.

#### [1.0.8] - 2016-10-20: A missing field from events

Version 1.0.8 is a small point release to expose the EventTimeSeries ID from
events received from a SignalFlow v2 computation. This field can then be used to
lookup the metadata of that EventTimeSeries from the computation.

```python
c = flow.execute(program)
for msg in c.stream():
    if isinstance(msg, signalfx.signalflow.messages.EventMessage):
        pprint.pprint(c.get_metadata(msg.tsid))
```

#### [1.0.7] - 2016-10-05: More Python 3 compatibility

Version 1.0.7 includes an updated version of the generated ProtocolBuffer code,
generated with version 3 of the Protocol Buffer compiler and library, which
produces Python 3 compatible Python source code.

#### [1.0.5] - 2016-09-29: Python 3 compatibility

Version 1.0.5 of the SignalFx Python client library provides compatibility for
Python 3.x.

#### [1.0.1] - 2016-06-02: Support for SignalFlow API

In version 1.0.1 of this client, we introduced support for the SignalFlow API.
This means you can use this client to programmatically stream analytical
computations from SignalFx in real time, in addition to sending data in to
SignalFx. Using SignalFlow, you can build your own applications that leverage
SignalFx's streaming analytics outside the SignalFx UI. To read more about
SignalFlow, click here: https://developers.signalfx.com/docs/signalflow-overview

Adding support for SignalFlow required upgrades to this client that are
backwards-incompatible with previous versions. Customers who are upgrading from
version 0.3.9 or earlier must change how the client is instantiated in
application code, and how it is authorized.

##### 1. Client instantiation

Each client's features are now divided among data transmission to SignalFx
(`ingest`), metadata retrieval (`rest`), and data streaming from SignalFx to
your client (`signalflow`).  This means that when you instantiate a SignalFx
client object, you must also choose which SignalFx API you will access using
that object.

- If you use the client to send data to SignalFx, use `ingest`.
- If you use the client to retrieve metric names and metadata from SignalFx,
  use `rest`.
- To use the new SignalFlow API to stream analytics to your client,
  use `signalflow`.

Before SignalFlow support, client instantiation used to look like this:

```python
import signalfx

sfx = signalfx.SignalFx('ACCESS_TOKEN')
```

After SignalFlow support, client instantiation now looks like this:

```python
import signalfx

sfx = signalfx.SignalFx()

# To send data from client to SignalFx using the ingest API
ingest = sfx.ingest('API_SESSION_TOKEN')

# To get and set properties and tags using the REST API
rest = sfx.rest('USER_SESSION_TOKEN')

# To stream data from SignalFx to client using the SignalFlow API
flow = sfx.signalflow('USER_SESSION_TOKEN')
```


##### 2. Authenticating to SignalFx

As illustrated in the above example, instead of supplying an access token at the
moment of instantiating a SignalFx client object, you must now supply it when
you choose which API to access.

- For `ingest`, supply your API session token. Obtain this token from within the
  SignalFx app.
- For `rest` and `signalflow`, first authenticate with your SignalFx credentials,
  then supply your user session token. [Click here to read about SignalFx authentication](https://developers.signalfx.com/docs/authentication-overview).

You can authenticate using cURL as in the following example:

```python
curl -s -XPOST -HContent-Type:application/json https://api.signalfx.com/v2/session -d'{"email":"USERNAME","password":"PASSWORD"}' | jq -r '.accessToken'
```

Alternatively, you could authenticate to SignalFx programmatically from within
this client:

```python
import signalfx
sfx = signalfx.SignalFx()
token = sfx.login("USERNAME", "PASSWORD")
```
