#!/usr/bin/env python

# Copyright (C) 2013-2015 SignalFuse, Inc.
# Copyright (C) 2015 SignalFx, Inc.

from setuptools import setup, find_packages

from signalfx.version import name, version

with open('README.md') as readme:
    long_description = readme.read()

setup(
    name=name,
    version=version,
    description='SignalFx Python support',
    long_description=long_description,
    zip_safe=True,
    packages=find_packages(),
    install_requires=[
        'requests==2.5.3',
    ],
    extras_require = {
        'pyformance': ['pyformance>=0.3.1'],
    },
    classifiers=[],
    url='https://github.com/signalfx/signalfx-python',
)
