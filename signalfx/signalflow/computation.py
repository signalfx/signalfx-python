# Copyright (C) 2016 SignalFx, Inc. All rights reserved.

from . import errors, messages


class Computation(object):
    """A live handle to a running SignalFlow computation."""

    STATE_UNKNOWN = 0
    STATE_STREAM_STARTED = 1
    STATE_COMPUTATION_STARTED = 2
    STATE_DATA_RECEIVED = 3
    STATE_COMPLETED = 4
    STATE_ABORTED = 5

    def __init__(self, exec_fn):
        self._id = None
        self._exec_fn = exec_fn

        self._stream = None
        self._state = Computation.STATE_UNKNOWN
        self._resolution = None
        self._num_input_timeseries = 0

        self._metadata = {}
        self._last_logical_ts = None

        self._expected_batches = 0
        self._batch_count_detected = False
        self._current_batch_message = None
        self._current_batch_count = 0

        self._find_matched_no_timeseries = False

        self._find_limited_resultset = False
        self._find_matched_size = 0
        self._find_limit_size = 0

        self._group_by_missing_property = False
        self._group_by_missing_properties = []

        # Kick it off.
        self._stream = self._execute()

    def _execute(self):
        return self._exec_fn(self._last_logical_ts)

    @property
    def id(self):
        return self._id

    @property
    def resolution(self):
        return self._resolution

    @property
    def num_input_timeseries(self):
        return self._num_input_timeseries

    @property
    def state(self):
        return self._state

    @property
    def last_logical_ts(self):
        return self._last_logical_ts

    @property
    def find_matched_no_timeseries(self):
        return self._find_matched_no_timeseries

    @property
    def find_limited_resultset(self):
        return self._find_limited_resultset

    @property
    def find_matched_size(self):
        return self._find_matched_size

    @property
    def find_limit_size(self):
        return self._find_limit_size

    @property
    def group_by_missing_property(self):
        return self._group_by_missing_property

    @property
    def group_by_missing_properties(self):
        return self._group_by_missing_properties

    def close(self):
        """Manually close this computation and detach from its stream.

        This computation object cannot be restarted, used or streamed for after
        this method is called."""
        self._state = Computation.STATE_COMPLETED
        if self._stream:
            self._stream.close()
            self._stream = None

    def get_known_tsids(self):
        return sorted(self._metadata.keys())

    def get_metadata(self, tsid):
        """Return the full metadata object for the given timeseries (by its
        ID), if available."""
        return self._metadata.get(tsid)

    def stream(self):
        """Iterate over the messages from the computation's output.

        Control and metadata messages are intercepted and interpreted to
        enhance this Computation's object knowledge of the computation's
        context. Data and event messages are yielded back to the caller as a
        generator.
        """

        iterator = iter(self._stream)
        while self._state < Computation.STATE_COMPLETED:
            try:
                message = next(iterator)
            except StopIteration:
                if self._state < Computation.STATE_COMPLETED:
                    self._stream = self._execute()
                    iterator = iter(self._stream)
                    continue
                break

            if isinstance(message, messages.StreamStartMessage):
                self._state = Computation.STATE_STREAM_STARTED
                continue

            if isinstance(message, messages.JobStartMessage):
                self._state = Computation.STATE_COMPUTATION_STARTED
                self._id = message.handle
                yield message
                continue

            if isinstance(message, messages.JobProgressMessage):
                yield message
                continue

            if isinstance(message, messages.ChannelAbortMessage):
                self._state = Computation.STATE_ABORTED
                raise errors.ComputationAborted(message.abort_info)

            if isinstance(message, messages.EndOfChannelMessage):
                self._state = Computation.STATE_COMPLETED
                continue

            # Intercept metadata messages to accumulate received metadata...
            if isinstance(message, messages.MetadataMessage):
                self._metadata[message.tsid] = message.properties
                yield message
                continue

            # ...as well as expired-tsid messages to clean it up.
            if isinstance(message, messages.ExpiredTsIdMessage):
                if message.tsid in self._metadata:
                    del self._metadata[message.tsid]
                yield message
                continue

            if isinstance(message, messages.InfoMessage):
                self._process_info_message(message.message)
                self._batch_count_detected = True
                yield message
                # TODO: InfoMessages are coming before DataMessages
                # if self._current_batch_message:
                #     yield self._get_batch_to_yield()
                continue

            # Accumulate data messages and release them when we have received
            # all batches for the same logical timestamp.
            if isinstance(message, messages.DataMessage):
                self._state = Computation.STATE_DATA_RECEIVED

                if not self._batch_count_detected:
                    self._expected_batches += 1

                if not self._current_batch_message:
                    self._current_batch_message = message
                    self._current_batch_count = 1
                elif (message.logical_timestamp_ms ==
                        self._current_batch_message.logical_timestamp_ms):
                    self._current_batch_message.add_data(message.data)
                    self._current_batch_count += 1
                else:
                    self._batch_count_detected = True

                if (self._batch_count_detected and
                        self._current_batch_count == self._expected_batches):
                    yield self._get_batch_to_yield()
                continue

            if isinstance(message, messages.EventMessage):
                yield message
                continue

            if isinstance(message, messages.ErrorMessage):
                raise errors.ComputationFailed(message.errors)

        # Yield last batch, even if potentially incomplete.
        if self._current_batch_message:
            yield self._get_batch_to_yield()

    def _process_info_message(self, message):
        """Process an information message received from the computation."""
        # Extract the output resolution from the appropriate message, if
        # it's present.
        contents = message.get('contents', None)
        if message['messageCode'] == 'JOB_RUNNING_RESOLUTION':
            self._resolution = contents['resolutionMs']
        elif message['messageCode'] == 'FETCH_NUM_TIMESERIES':
            self._num_input_timeseries += int(message['numInputTimeSeries'])
        elif message['messageCode'] == 'FIND_MATCHED_NO_TIMESERIES':
            self._find_matched_no_timeseries = True
        elif message['messageCode'] == 'FIND_LIMITED_RESULT_SET':
            self._find_limited_resultset = True
            self._find_matched_size = contents['matchedSize']
            self._find_limit_size = contents['limitSize']
        elif message['messageCode'] == 'GROUPBY_MISSING_PROPERTY':
            self._group_by_missing_property = True
            self._group_by_missing_properties = contents['propertyNames']

    def _get_batch_to_yield(self):
        to_yield = self._current_batch_message
        self._current_batch_message = None
        self._current_batch_count = 0
        self._last_logical_ts = to_yield.logical_timestamp_ms
        return to_yield
