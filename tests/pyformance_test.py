#!/usr/bin/env python

# Copyright (C) 2017 SignalFx, Inc. All rights reserved.

from pyformance.registry import get_qualname
import os
import sys
import unittest

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..'))

# import the signalfx pyformance library
import signalfx.pyformance as pyf # noqa


class TestPyformance(unittest.TestCase):
    def tearDown(self):
        pyf.clear()

    def test_gauge(self):
        reg = pyf.MetricsRegistry()
        reg.gauge('test_gauge').set_value(1)
        reg.gauge('test_gauge_with_dim', default=3,
                  gauge_dim='hello_gauge').set_value(2)
        self.assertEqual(
            reg.metadata.get_metadata(
                'gauge_dim=hello_gauge.test_gauge_with_dim'),
            {
                'dimensions': {'gauge_dim': 'hello_gauge'},
                'metric': 'test_gauge_with_dim',
            })
        self.assertEqual(reg.dump_metrics(), {
                'test_gauge': {'value': 1},
                'gauge_dim=hello_gauge.test_gauge_with_dim': {'value': 2},
            }
        )
        reg.clear()
        self.assertEqual(reg.dump_metrics(), {})
        self.assertEqual(len(reg.metadata._metadata), 0)

    def test_global_gauge(self):
        pyf.gauge('test_gauge').set_value(1)
        pyf.gauge('test_gauge_with_dim', default=3,
                  gauge_dim='hello_gauge').set_value(2)
        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'gauge_dim=hello_gauge.test_gauge_with_dim'),
            {
                'dimensions': {'gauge_dim': 'hello_gauge'},
                'metric': 'test_gauge_with_dim',
            })
        self.assertEqual(pyf.dump_metrics(), {
                'test_gauge': {'value': 1},
                'gauge_dim=hello_gauge.test_gauge_with_dim': {'value': 2},
            }
        )

    def test_counter(self):
        reg = pyf.MetricsRegistry()
        reg.counter('test_counter').inc()
        reg.counter('test_counter_with_dim',
                    counter_dim='hello_counter').inc()
        self.assertEqual(
            reg.metadata.get_metadata(
                'counter_dim=hello_counter.test_counter_with_dim'),
            {
                'dimensions': {'counter_dim': 'hello_counter'},
                'metric': 'test_counter_with_dim',
            })
        self.assertEqual(reg.dump_metrics(), {
            'test_counter': {'count': 1},
            'counter_dim=hello_counter.test_counter_with_dim': {'count': 1},
        })
        reg.clear()
        self.assertEqual(reg.dump_metrics(), {})
        self.assertEqual(len(reg.metadata._metadata), 0)

    def test_global_counter(self):
        pyf.counter('test_counter').inc()
        pyf.counter('test_counter_with_dim',
                    counter_dim='hello_counter').inc()
        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'counter_dim=hello_counter.test_counter_with_dim'),
            {
                'dimensions': {'counter_dim': 'hello_counter'},
                'metric': 'test_counter_with_dim',
            })
        self.assertEqual(pyf.dump_metrics(), {
            'test_counter': {'count': 1},
            'counter_dim=hello_counter.test_counter_with_dim': {'count': 1},
        })

    def test_counter_decorator(self):
        @pyf.count_calls
        def callme():
            pass

        qcallme = get_qualname(callme)

        @pyf.count_calls_with_dims(counter_dim='hello_counter')
        def callme_with_dims():
            pass

        qcallme_with_dims = get_qualname(callme_with_dims)

        callme()
        callme_with_dims()
        if sys.version_info[0] < 3:
            self.assertEqual(
                pyf.global_registry().metadata.get_metadata(
                    'counter_dim=hello_counter.{0}_calls'.format(
                        qcallme_with_dims)),
                {
                    'dimensions': {'counter_dim': 'hello_counter'},
                    'metric': '{0}_calls'.format(qcallme_with_dims),
                })
            self.assertEqual(pyf.dump_metrics(), {
                '{0}_calls'.format(qcallme): {'count': 1},
                'counter_dim=hello_counter.{0}_calls'.format(
                    qcallme_with_dims):
                {'count': 1},
            })

    def test_histogram(self):
        reg = pyf.MetricsRegistry()
        h1 = reg.histogram('test_histogram')
        h1.add(1)
        h1.add(1)
        h1.add(1)
        h2 = reg.histogram('test_histogram_with_dim',
                           histogram_dim='hello_histogram')
        h2.add(1)
        h2.add(1)
        h2.add(1)

        metrics = reg.dump_metrics()
        self.assertEqual(metrics, {
            'test_histogram': {'count': 3, '999_percentile': 1,
                               '99_percentile': 1, 'min': 1,
                               '95_percentile': 1, '75_percentile': 1,
                               'std_dev': 0.0, 'max': 1, 'avg': 1.0},
            'histogram_dim=hello_histogram.test_histogram_with_dim':
            {'count': 3, '999_percentile': 1, '99_percentile': 1, 'min': 1,
             '95_percentile': 1, '75_percentile': 1, 'std_dev': 0.0,
             'max': 1, 'avg': 1.0},
        })
        reg.clear()
        self.assertEqual(reg.dump_metrics(), {})
        self.assertEqual(len(reg.metadata._metadata), 0)

    def test_global_histogram(self):
        h1 = pyf.histogram('test_histogram')
        h1.add(1)
        h1.add(1)
        h1.add(1)
        h2 = pyf.histogram('test_histogram_with_dim',
                           histogram_dim='hello_histogram')
        h2.add(1)
        h2.add(1)
        h2.add(1)
        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'histogram_dim=hello_histogram.test_histogram_with_dim'),
            {
                'dimensions': {'histogram_dim': 'hello_histogram'},
                'metric': 'test_histogram_with_dim',
            })
        self.assertEqual(pyf.dump_metrics(), {
            'test_histogram': {'count': 3, '999_percentile': 1,
                               '99_percentile': 1, 'min': 1,
                               '95_percentile': 1, '75_percentile': 1,
                               'std_dev': 0.0, 'max': 1, 'avg': 1.0},
            'histogram_dim=hello_histogram.test_histogram_with_dim':
            {'count': 3, '999_percentile': 1, '99_percentile': 1, 'min': 1,
             '95_percentile': 1, '75_percentile': 1, 'std_dev': 0.0,
             'max': 1, 'avg': 1.0},
        })

    def test_histogram_decorator(self):
        @pyf.hist_calls
        def callme():
            return 1

        qcallme = get_qualname(callme)

        @pyf.hist_calls_with_dims(histogram_dim='hello_histogram')
        def callme_with_dims():
            return 1

        qcallme_with_dims = get_qualname(callme_with_dims)

        callme()
        callme()
        callme()
        callme_with_dims()
        callme_with_dims()
        callme_with_dims()

        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'histogram_dim=hello_histogram.{0}_calls'.format(
                    qcallme_with_dims)),
            {
                'dimensions': {'histogram_dim': 'hello_histogram'},
                'metric': '{0}_calls'.format(qcallme_with_dims),
            })
        self.assertEqual(pyf.dump_metrics(), {
            '{0}_calls'.format(qcallme): {
                'count': 3, '999_percentile': 1,
                '99_percentile': 1, 'min': 1,
                '95_percentile': 1, '75_percentile': 1,
                'std_dev': 0.0, 'max': 1, 'avg': 1.0},
            'histogram_dim=hello_histogram.{0}_calls'.format(
                qcallme_with_dims):
            {'count': 3, '999_percentile': 1, '99_percentile': 1, 'min': 1,
                '95_percentile': 1, '75_percentile': 1, 'std_dev': 0.0,
                'max': 1, 'avg': 1.0},
        })

    def test_meter(self):
        reg = pyf.MetricsRegistry()
        reg.meter('test_meter')
        reg.meter('test_meter_with_dim',
                  meter_dim='hello_meter')
        self.assertEqual(
            reg.metadata.get_metadata(
                'meter_dim=hello_meter.test_meter_with_dim'),
            {
                'dimensions': {'meter_dim': 'hello_meter'},
                'metric': 'test_meter_with_dim',
            })
        self.assertEqual(len(reg.dump_metrics()), 2)
        reg.clear()
        self.assertEqual(reg.dump_metrics(), {})
        self.assertEqual(len(reg.metadata._metadata), 0)

    def test_global_meter(self):
        pyf.meter('test_meter')
        pyf.meter('test_meter_with_dim', meter_dim='hello_meter')
        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'meter_dim=hello_meter.test_meter_with_dim'),
            {
                'dimensions': {'meter_dim': 'hello_meter'},
                'metric': 'test_meter_with_dim',
            })
        self.assertEqual(len(pyf.dump_metrics()), 2)

    def test_meter_decorator(self):
        @pyf.meter_calls
        def callme():
            return 1

        @pyf.meter_calls_with_dims(meter_dim='hello_meter')
        def callme_with_dims():
            return 1

        qcallme_with_dims = get_qualname(callme_with_dims)

        callme()
        callme()
        callme()
        callme_with_dims()
        callme_with_dims()
        callme_with_dims()

        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'meter_dim=hello_meter.{0}_calls'.format(qcallme_with_dims)),
            {
                'dimensions': {'meter_dim': 'hello_meter'},
                'metric': '{0}_calls'.format(qcallme_with_dims),
            })
        self.assertEqual(len(pyf.dump_metrics()), 2)

    def test_timer(self):
        reg = pyf.MetricsRegistry()
        reg.timer('test_timer')
        reg.timer('test_timer_with_dim',
                  timer_dim='hello_timer')
        self.assertEqual(
            reg.metadata.get_metadata(
                'timer_dim=hello_timer.test_timer_with_dim'),
            {
                'dimensions': {'timer_dim': 'hello_timer'},
                'metric': 'test_timer_with_dim',
            })
        self.assertEqual(len(reg.dump_metrics()), 2)
        reg.clear()
        self.assertEqual(reg.dump_metrics(), {})
        self.assertEqual(len(reg.metadata._metadata), 0)

    def test_global_timer(self):
        pyf.timer('test_timer')
        pyf.timer('test_timer_with_dim', timer_dim='hello_timer')
        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'timer_dim=hello_timer.test_timer_with_dim'),
            {
                'dimensions': {'timer_dim': 'hello_timer'},
                'metric': 'test_timer_with_dim',
            })
        self.assertEqual(len(pyf.dump_metrics()), 2)

    def test_timer_decorator(self):
        @pyf.time_calls
        def callme():
            return 1

        @pyf.time_calls_with_dims(timer_dim='hello_timer')
        def callme_with_dims():
            return 1

        qcallme_with_dims = get_qualname(callme_with_dims)

        callme()
        callme()
        callme()
        callme_with_dims()
        callme_with_dims()
        callme_with_dims()

        self.assertEqual(
            pyf.global_registry().metadata.get_metadata(
                'timer_dim=hello_timer.{0}_calls'.format(qcallme_with_dims)),
            {
                'dimensions': {'timer_dim': 'hello_timer'},
                'metric': '{0}_calls'.format(qcallme_with_dims),
            })
        self.assertEqual(len(pyf.dump_metrics()), 2)


if __name__ == '__main__':
    unittest.main()
