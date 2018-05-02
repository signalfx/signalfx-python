# Copyright (C) 2018 SignalFx, Inc. All rights reserved.


class MetricMetadata(object):
    """Metric dimensions metadata repository.

    This class mediates the registration of metrics with additional dimensions
    and registers the metrics in the Pyformance registry using a unique
    composite name, while recording the mapping from composite name to the
    original metric name and dimensions.

    It then makes this information available to the SignalFxReporter so metrics
    can be reported with the appropriate metric and dimensions.
    """

    def __init__(self):
        self._metadata = {}

    def get_metadata(self, key):
        """Returns metadata for the specified key"""
        dimensions = self._metadata.get(key)
        return dimensions or {}

    def register(self, key, **kwargs):
        """Registers metadata for a metric and returns a composite key"""
        dimensions = dict((k, str(v)) for k, v in kwargs.items())
        composite_key = self._composite_name(key, dimensions)
        self._metadata[composite_key] = {
            'metric': key,
            'dimensions': dimensions
        }
        return composite_key

    def _composite_name(self, metric_name, dimensions=None):
        composite = []
        if dimensions:
            for key in sorted(dimensions.keys()):
                composite.append('{}={}'.format(key, dimensions[key]))
        composite.append(metric_name)
        return '.'.join(composite)

    def clear(self):
        """Clears the registered metadata"""
        self._metadata.clear()
