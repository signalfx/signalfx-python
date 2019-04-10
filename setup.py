#!/usr/bin/env python

# Copyright (C) 2013-2014 SignalFuse, Inc. All rights reserved.
# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

from setuptools import setup, find_packages

with open('signalfx/version.py') as f:
    exec(f.read())

with open('README.rst') as readme:
    long_description = readme.read()

test_requirements = ['httmock']

with open('requirements.txt') as f:
    requirements = [line.strip() for line in f.readlines()]

setup(
    name=name,  # noqa
    version=version,  # noqa
    author='SignalFx, Inc',
    author_email='info@signalfx.com',
    description='SignalFx Python Library',
    license='Apache Software License v2',
    long_description=long_description,
    zip_safe=True,
    packages=find_packages(),
    install_requires=requirements,
    tests_require=test_requirements,
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    url='https://github.com/signalfx/signalfx-python',
)
