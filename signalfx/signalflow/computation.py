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

        self._metadata = {}
        self._last_logical_ts = None

        # Kick it off.
        self._execute()

    @property
    def id(self):
        return self._id

    @property
    def resolution(self):
        return self._resolution

    @property
    def state(self):
        return self._state

    def _execute(self):
        self._stream = self._exec_fn(self._last_logical_ts)

    def close(self):
        """Manually close this computation and detach from its stream.

        This computation object cannot be restarted, used or streamed for after
        this method is called."""
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

        last_data_batch = None
        iterator = iter(self._stream)
        while self._state < Computation.STATE_COMPLETED:
            try:
                message = next(iterator)
            except StopIteration:
                if self._state < Computation.STATE_COMPLETED:
                    self._stream = self._execute()
                    continue

            if isinstance(message, messages.StreamStartMessage):
                self._state = Computation.STATE_STREAM_STARTED
                continue

            if isinstance(message, messages.JobStartMessage):
                self._state = Computation.STATE_COMPUTATION_STARTED
                self._id = message.handle
                continue

            if isinstance(message, messages.ChannelAbortMessage):
                self._state = Computation.STATE_ABORTED
                raise errors.ComputationAborted(message.abort_info)

            if isinstance(message, messages.EndOfChannelMessage):
                self._state = Computation.STATE_COMPLETED
                continue

            # Intercept metadata messages to accumulate received metadata.
            # TODO(mpetazzoni): this can accumulate metadata without bounds if
            # a computation has a high rate of member churn.
            if isinstance(message, messages.MetadataMessage):
                self._metadata[message.tsid] = message.properties
                continue

            if isinstance(message, messages.InfoMessage):
                self._process_info_message(message.message)
                continue

            # Accumulate data messages and release them when we have received
            # all batches for the same logical timestamp.
            if isinstance(message, messages.DataMessage):
                self._state = Computation.STATE_DATA_RECEIVED
                if not last_data_batch:
                    last_data_batch = message
                elif message.logical_timestamp_ms == \
                        last_data_batch.logical_timestamp_ms:
                    last_data_batch.add_data(message.data)
                else:
                    to_yield, last_data_batch = last_data_batch, message
                    self._last_logical_ts = to_yield.logical_timestamp_ms
                    yield to_yield
                continue

            # Automatically and immediately yield all other messages.
            yield message

        # Yield last batch, even if potentially incomplete.
        if last_data_batch:
            yield last_data_batch

    def _process_info_message(self, message):
        """Process an information message received from the computation."""
        # Extract the output resolution from the appropriate message, if
        # it's present.
        if message['messageCode'] == 'JOB_RUNNING_RESOLUTION':
            self._resolution = message['contents']['resolutionMs']
