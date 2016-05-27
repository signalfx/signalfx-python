#!/usr/bin/env python

# Copyright (C) 2013-2014 SignalFuse, Inc. All rights reserved.
# Copyright (C) 2015-2016 SignalFx, Inc. All rights reserved.

from setuptools import setup, find_packages


execfile('signalfx/version.py')

with open('README.md') as readme:
    long_description = readme.read()

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
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ],
    url='https://github.com/signalfx/signalfx-python',
)
